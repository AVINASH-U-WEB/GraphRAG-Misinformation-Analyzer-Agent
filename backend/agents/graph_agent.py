# backend/agents/graph_agent.py
import json
import asyncio
from services.neo4j_service import neo4j_service
from services.groq_service import groq_service
from utils.helpers import clean_text, extract_hashtags, extract_mentions, format_timestamp, serialize_neo4j_value
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphAgent:
    def __init__(self):
        self.neo4j = neo4j_service
        self.groq = groq_service

    async def _extract_with_groq(self, text: str) -> dict:
        prompt = """
        You are an expert information extraction AI. Analyze the provided text and respond ONLY with a valid JSON object containing these keys: "claims", "entities", "summary", "keywords".
        Example: { "claims": ["Statement 1."], "entities": ["Entity A"], "summary": "A summary.", "keywords": ["keyword1"] }
        """
        try:
            response_json_str = await self.groq.invoke_llm_chain(
                system_prompt=prompt, user_message=f"Text to analyze: {text}", model_type="accurate"
            )
            json_match_start = response_json_str.find('{')
            json_match_end = response_json_str.rfind('}') + 1
            if json_match_start == -1 or json_match_end == 0:
                raise json.JSONDecodeError("No JSON object found in LLM response", response_json_str, 0)
            json_match = response_json_str[json_match_start:json_match_end]
            return json.loads(json_match)
        except Exception as e:
            logger.error(f"Groq extraction failed or returned invalid JSON: {e}")
            return {"claims": [], "entities": [], "summary": "", "keywords": []}

    async def process_post(self, post_data: dict) -> dict:
        """
        This is the DEFINITIVE, FINAL version, built specifically for the 'supergoose/.../healthfact_classification' dataset.
        """
        # THE DEFINITIVE FIX 1: Look for the text in the correct 'inputs_pretokenized' column.
        post_text_raw = post_data.get('inputs_pretokenized')
        
        if not post_text_raw or not isinstance(post_text_raw, str):
            post_id_for_error = post_data.get('id', 'unknown_id')
            logger.warning(f"SKIPPING item. Reason: The 'inputs_pretokenized' field is missing or invalid. Data: {post_data}")
            return {"post_id": post_id_for_error, "status": "error", "message": "Input data is missing a valid text field."}
        
        post_id = post_data.get('id') or f"temp_id_{hash(post_text_raw)}"
        post_text = clean_text(post_text_raw)
        author_name = post_data.get('author') or "Unknown"
        timestamp_str = post_data.get('date')
        formatted_timestamp = format_timestamp(timestamp_str) if timestamp_str else None
        
        # THE DEFINITIVE FIX 2: Look for the verdict in the correct 'targets_pretokenized' column.
        verdict_text = post_data.get('targets_pretokenized')
        external_verdict_value = None
        if isinstance(verdict_text, str):
            if "true" in verdict_text.lower():
                external_verdict_value = "True"
            elif "false" in verdict_text.lower():
                external_verdict_value = "False"

        verdict_source = "DatasetLabel"
        groq_extracted_data = await self._extract_with_groq(post_text)
        
        params = {
            "postId": post_id, "postContent": post_text, "postSummary": groq_extracted_data.get('summary', ''),
            "authorName": author_name, "timestampValue": formatted_timestamp,
            "claimsList": groq_extracted_data.get('claims', []), "entitiesList": groq_extracted_data.get('entities', []),
            "keywordsList": groq_extracted_data.get('keywords', []), "hashtagsList": extract_hashtags(post_text),
            "mentionsList": extract_mentions(post_text), "verdictValue": external_verdict_value, "verdictSource": verdict_source
        }
        query = """
        MERGE (p:Post {id: $postId})
          ON CREATE SET p.content = $postContent, p.summary = $postSummary, p.createdAt = datetime()
          ON MATCH SET p.content = $postContent, p.summary = $postSummary, p.updatedAt = datetime()
        MERGE (a:Author {name: $authorName}) MERGE (a)-[:CREATED]->(p)
        WITH p
        FOREACH (_ IN CASE WHEN $timestampValue IS NOT NULL THEN [1] ELSE [] END |
            MERGE (t:Timestamp {value: $timestampValue}) MERGE (p)-[:AT_TIME]->(t)
        )
        FOREACH (_ IN CASE WHEN $verdictValue IS NOT NULL THEN [1] ELSE [] END |
            MERGE (v:FactCheckVerdict {value: $verdictValue})
            MERGE (s:FactCheckSource {name: $verdictSource})
            MERGE (p)-[:HAS_VERDICT]->(v) MERGE (v)-[:FROM_SOURCE]->(s)
        )
        FOREACH (claimText IN $claimsList | MERGE (c:Claim {text: claimText}) MERGE (p)-[:CONTAINS_CLAIM]->(c) )
        FOREACH (entityName IN $entitiesList | MERGE (e:Entity {name: entityName}) MERGE (p)-[:MENTIONS]->(e) )
        FOREACH (keywordText IN $keywordsList | MERGE (k:Keyword {text: keywordText}) MERGE (p)-[:HAS_KEYWORD]->(k) )
        FOREACH (hashtagTag IN $hashtagsList | MERGE (h:Hashtag {tag: hashtagTag}) MERGE (p)-[:HAS_HASHTAG]->(h) )
        FOREACH (mentionName IN $mentionsList | MERGE (m:Entity {name: mentionName}) MERGE (p)-[:MENTIONS_USER]->(m) )
        RETURN p.id AS postId
        """
        
        try:
            results = await asyncio.to_thread(self.neo4j.run_query, query, params)
            if results and results[0].get('postId') == post_id:
                return {"post_id": post_id, "status": "success", "graph_data_inserted": True}
            else:
                return {"post_id": post_id, "status": "error", "message": "Graph insertion could not be confirmed."}
        except Exception as e:
            logger.error(f"Failed to create/update graph for post {post_id}: {e}")
            raise

    async def get_post_graph(self, post_id: str):
        # This code is correct and does not need to change
        query = "MATCH (p:Post {id: $postId}) CALL apoc.path.subgraphAll(p, { maxLevel: 2 }) YIELD nodes, relationships RETURN nodes, relationships"
        try:
            records = await asyncio.to_thread(self.neo4j.run_query, query, {"postId": post_id})
            nodes_map, links = {}, []
            if not records: return {"nodes": [], "links": []}
            record = records[0]
            for node in record.get('nodes', []):
                node_id = node.get('id', node.element_id)
                nodes_map[node.element_id] = { "id": str(node_id), "labels": list(node.labels), "properties": serialize_neo4j_value(dict(node)) }
            for rel in record.get('relationships', []):
                if rel.start_node.element_id in nodes_map and rel.end_node.element_id in nodes_map:
                    links.append({ "source": str(nodes_map[rel.start_node.element_id]['id']), "target": str(nodes_map[rel.end_node.element_id]['id']), "type": rel.type, "properties": serialize_neo4j_value(dict(rel)) })
            return {"nodes": list(nodes_map.values()), "links": links}
        except Exception as e:
            if "Unknown function 'apoc.path.subgraphAll'" in str(e):
                logger.warning("APOC not found, using fallback query for get_post_graph.")
                return await self.get_post_graph_fallback(post_id)
            logger.error(f"Error retrieving graph for post {post_id}: {e}")
            raise

    async def get_post_graph_fallback(self, post_id: str):
        # This code is correct and does not need to change
        query = "MATCH (p:Post {id: $postId}) OPTIONAL MATCH (p)-[r]-(n) RETURN p, r, n"
        records = await asyncio.to_thread(self.neo4j.run_query, query, {"postId": post_id})
        nodes_map, links_set = {}, set()
        for record in records:
            p_node = record['p']; n_node = record['n']; rel = record['r']
            if p_node:
                p_id = p_node.get('id', p_node.element_id)
                nodes_map[p_node.element_id] = {"id": str(p_id), "labels": list(p_node.labels), "properties": serialize_neo4j_value(dict(p_node))}
            if n_node:
                n_id = n_node.get('id', n_node.element_id)
                nodes_map[n_node.element_id] = {"id": str(n_id), "labels": list(n_node.labels), "properties": serialize_neo4j_value(dict(n_node))}
            if rel:
                source_id, target_id = str(nodes_map[rel.start_node.element_id]['id']), str(nodes_map[rel.end_node.element_id]['id'])
                links_set.add((source_id, target_id, rel.type))
        links = [{"source": s, "target": t, "type": typ} for s, t, typ in links_set]
        return {"nodes": list(nodes_map.values()), "links": links}

    async def get_summary_and_verdict(self, post_id: str):
        # This code is correct and does not need to change
        query = "MATCH (p:Post {id: $postId}) OPTIONAL MATCH (p)-[:HAS_VERDICT]->(v:FactCheckVerdict)-[:FROM_SOURCE]->(s:FactCheckSource) RETURN p.summary AS summary, v.value AS verdict, s.name AS verdictSource"
        try:
            records = await asyncio.to_thread(self.neo4j.run_query, query, {"postId": post_id})
            return records[0].data() if records else None
        except Exception as e:
            logger.error(f"Error retrieving summary/verdict for post {post_id}: {e}")
            raise

graph_agent = GraphAgent()
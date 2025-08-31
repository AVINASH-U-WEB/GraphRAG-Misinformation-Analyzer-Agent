# backend/routes/graph_routes.py
from flask import Blueprint, request, jsonify
from agents.graph_agent import graph_agent
from agents.dataset_loader import dataset_loader
from models.graph_models import PostData, DatasetLoadRequest, FactCheckVerdictData
from werkzeug.exceptions import BadRequest, InternalServerError
import asyncio
import logging
from config import Config

logger = logging.getLogger()

graph_bp = Blueprint('graph_routes', __name__)

@graph_bp.route('/process-post', methods=['POST'])
async def process_single_post():
    if not request.is_json: raise BadRequest("Request must be JSON.")
    try:
        post_data = PostData(**request.json)
        result = await graph_agent.process_post(post_data.model_dump())
        return jsonify(result), 200
    except Exception as e:
        logger.exception(f"Error processing single post: {e}")
        raise InternalServerError(f"Failed to process post: {e}")

@graph_bp.route('/load-dataset', methods=['POST'])
async def load_huggingface_dataset():
    if not request.is_json: raise BadRequest("Request must be JSON.")
    if not Config.GROQ_API_KEY:
        logger.error("CRITICAL ERROR: GROQ_API_KEY is not set.")
        raise InternalServerError("Server configuration error: GROQ_API_KEY is missing.")

    try:
        load_request = DatasetLoadRequest(**request.json)
    except Exception as e:
        raise BadRequest(f"Invalid input data: {e}")

    try:
        logger.info(f"Loading dataset: {load_request.dataset_name}...")
        hf_dataset = dataset_loader.load_hf_dataset(
            load_request.dataset_name,
            load_request.config_name,
            load_request.split
        )
        
        # =======================================================================
        # THE FIX: This new line limits the dataset to the first 1000 items.
        # =======================================================================
        hf_dataset = hf_dataset.select(range(200))
        logger.info(f"Processing a limited set of {len(hf_dataset)} items.")
        # =======================================================================

        all_results = []
        tasks = []
        CONCURRENT_BATCH_SIZE = 3 
        DELAY_BETWEEN_BATCHES_SECONDS = 1

        for i, item in enumerate(hf_dataset):
            item_id_text = item.get('input') or item.get('claim') or item.get('text', '')
            item['id'] = f"{load_request.dataset_name.replace('/', '_')}_{load_request.split}_{i}"
            tasks.append(graph_agent.process_post(item))
            
            if len(tasks) >= CONCURRENT_BATCH_SIZE:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                all_results.extend(batch_results)
                tasks = []
                logger.info(f"Processed batch. Total items handled: {len(all_results)} / {len(hf_dataset)}. Waiting for {DELAY_BETWEEN_BATCHES_SECONDS}s...")
                await asyncio.sleep(DELAY_BETWEEN_BATCHES_SECONDS)

        if tasks:
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            all_results.extend(batch_results)
            logger.info(f"Processed final batch. Total items handled: {len(all_results)} / {len(hf_dataset)}")

        successful_ids = []
        failed_count = 0
        for i, res in enumerate(all_results):
            if isinstance(res, dict) and res.get('status') == 'success':
                successful_ids.append(res['post_id'])
            else:
                failed_count += 1
                logger.error(f"Failed to process item index {i}. Reason: {res}")

        return jsonify({
            "status": "Dataset processing completed",
            "total_items": len(hf_dataset), # This will now be 1000
            "processed_successfully": len(successful_ids),
            "failed_to_process": failed_count,
            "sample_of_processed_ids": successful_ids[:10],
            "note": "Check server logs for detailed error messages on failed items."
        }), 200

    except Exception as e:
        logger.exception(f"A critical error occurred during dataset loading: {e}")
        raise InternalServerError(f"Failed to load and process dataset: {e}")

# --- The rest of the routes do not need changes ---
@graph_bp.route('/post-graph/<string:post_id>', methods=['GET'])
async def get_post_graph_data(post_id: str):
    # ... (code remains the same)
    try:
        graph_data = await graph_agent.get_post_graph(post_id)
        if not graph_data or not graph_data['nodes']:
            return jsonify({"message": "Post not found or no graph data available.", "post_id": post_id}), 404
        return jsonify(graph_data), 200
    except Exception as e:
        logger.exception(f"Error retrieving graph for post {post_id}: {e}")
        raise InternalServerError(f"Failed to retrieve graph data: {e}")

@graph_bp.route('/post-summary/<string:post_id>', methods=['GET'])
async def get_post_summary_and_verdict(post_id: str):
    # ... (code remains the same)
    try:
        summary_data = await graph_agent.get_summary_and_verdict(post_id)
        if not summary_data:
            return jsonify({"message": "Summary or verdict not found for this post.", "post_id": post_id}), 404
        return jsonify(summary_data), 200
    except Exception as e:
        logger.exception(f"Error retrieving summary/verdict for post {post_id}: {e}")
        raise InternalServerError(f"Failed to retrieve summary and verdict: {e}")

@graph_bp.route('/update-verdict', methods=['POST'])
async def update_post_verdict():
    # ... (code remains the same)
    if not request.is_json: raise BadRequest("Request must be JSON.")
    try:
        verdict_data = FactCheckVerdictData(**request.json)
        query = "MATCH (p:Post {id: $postId}) MERGE (v:FactCheckVerdict {value: $verdictValue}) MERGE (s:FactCheckSource {name: $sourceName}) MERGE (p)-[:HAS_VERDICT]->(v) MERGE (v)-[:FROM_SOURCE]->(s)"
        params = {"postId": verdict_data.post_id, "verdictValue": verdict_data.verdict, "sourceName": verdict_data.source or "ManualUpdate"}
        await asyncio.to_thread(graph_agent.neo4j.run_query, query, params)
        return jsonify({"status": "success", "message": f"Verdict for post {verdict_data.post_id} updated."}), 200
    except Exception as e:
        logger.exception(f"Error updating verdict for post {verdict_data.post_id}: {e}")
        raise InternalServerError(f"Failed to update verdict: {e}")
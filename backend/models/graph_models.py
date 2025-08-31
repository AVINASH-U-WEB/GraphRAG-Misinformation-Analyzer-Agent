# backend/models/graph_models.py
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any

class PostData(BaseModel):
    """
    Model for a single social media post or article input.
    """
    id: Optional[str] = Field(None, description="Unique identifier for the post. If not provided, one will be generated.")
    text: str = Field(..., description="The main content/text of the post or article.")
    author: Optional[str] = Field(None, description="The author's name or username.")
    date: Optional[str] = Field(None, description="The publication/post date (e.g., ISO 8601 string).")
    url: Optional[HttpUrl] = Field(None, description="Original URL of the post/article.")
    # For dataset integration, a 'label' might be present
    label: Optional[str] = Field(None, description="Pre-existing fact-check label (e.g., 'True', 'Fake').")
    
    # You can add more fields here relevant to your specific social media inputs
    # e.g., 'platform': Optional[str], 'likes': Optional[int], 'shares': Optional[int]

class DatasetLoadRequest(BaseModel):
    """
    Model for requesting to load a Hugging Face dataset.
    """
    dataset_name: str = Field(..., description="Name of the Hugging Face dataset (e.g., 'liar_dataset').")
    config_name: Optional[str] = Field(None, description="Specific configuration name for the dataset (if applicable).")
    split: str = Field("train", description="Dataset split to load (e.g., 'train', 'validation', 'test').")

class FactCheckVerdictData(BaseModel):
    """
    Model for updating a fact-check verdict for a specific post.
    """
    post_id: str = Field(..., description="The unique ID of the post to update.")
    verdict: str = Field(..., description="The fact-check verdict (e.g., 'True', 'Fake', 'Misleading').")
    source: Optional[str] = Field("Manual Update", description="The source of the fact-check verdict.")
    # Potentially add more details like 'confidence_score', 'evidence_url'

# Example for graph visualization response structure
# (though the agent returns nodes/links directly, this is good for documentation)
class GraphNode(BaseModel):
    id: str
    labels: List[str]
    properties: Dict[str, Any]

class GraphLink(BaseModel):
    source: str
    target: str
    type: str
    properties: Dict[str, Any]

class GraphData(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphLink]
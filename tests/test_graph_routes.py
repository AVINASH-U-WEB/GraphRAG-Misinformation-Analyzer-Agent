import pytest
from flask import Flask
from backend.routes.graph_routes import graph_bp
import json
from unittest.mock import patch, MagicMock

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(graph_bp)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

# Test data fixtures
@pytest.fixture
def sample_post_data():
    return {
        "id": "test_post_1",
        "content": "Test content",
        "source": "twitter",
        "timestamp": "2024-01-01T00:00:00Z"
    }

@pytest.fixture
def sample_dataset_request():
    return {
        "dataset_name": "test_dataset",
        "config_name": "default",
        "split": "train"
    }

# Test process-post endpoint
async def test_process_post(client, sample_post_data):
    with patch('backend.routes.graph_routes.graph_agent') as mock_agent:
        mock_agent.process_post.return_value = {"status": "success", "post_id": "test_post_1"}
        
        response = await client.post('/process-post',
                                   json=sample_post_data,
                                   content_type='application/json')
        
        assert response.status_code == 200
        assert response.json['status'] == 'success'

# Test load-dataset endpoint
async def test_load_dataset(client, sample_dataset_request):
    with patch('backend.routes.graph_routes.dataset_loader') as mock_loader, \
         patch('backend.routes.graph_routes.graph_agent') as mock_agent:
        
        mock_loader.load_hf_dataset.return_value = [{"id": "1", "content": "test"}]
        mock_agent.process_post.return_value = {"status": "success", "post_id": "1"}
        
        response = await client.post('/load-dataset',
                                   json=sample_dataset_request,
                                   content_type='application/json')
        
        assert response.status_code == 200
        assert response.json['total_items'] == 1

# Test get-post-graph endpoint
async def test_get_post_graph(client):
    test_graph_data = {
        "nodes": [{"id": "1", "label": "Post"}],
        "links": []
    }
    
    with patch('backend.routes.graph_routes.graph_agent') as mock_agent:
        mock_agent.get_post_graph.return_value = test_graph_data
        
        response = await client.get('/post-graph/test_post_1')
        
        assert response.status_code == 200
        assert response.json == test_graph_data

# Test post-summary endpoint
async def test_get_post_summary(client):
    test_summary = {
        "summary": "Test summary",
        "verdict": "TRUE"
    }
    
    with patch('backend.routes.graph_routes.graph_agent') as mock_agent:
        mock_agent.get_summary_and_verdict.return_value = test_summary
        
        response = await client.get('/post-summary/test_post_1')
        
        assert response.status_code == 200
        assert response.json == test_summary

# Test update-verdict endpoint
async def test_update_verdict(client):
    verdict_data = {
        "post_id": "test_post_1",
        "verdict": "FALSE",
        "source": "manual"
    }
    
    with patch('backend.routes.graph_routes.graph_agent') as mock_agent:
        mock_agent.neo4j.run_query = MagicMock()
        
        response = await client.post('/update-verdict',
                                   json=verdict_data,
                                   content_type='application/json')
        
        assert response.status_code == 200
        assert "success" in response.json['status']

# Test error cases
async def test_invalid_post_data(client):
    invalid_data = {"wrong_field": "test"}
    
    response = await client.post('/process-post',
                               json=invalid_data,
                               content_type='application/json')
    
    assert response.status_code == 400

async def test_missing_post_graph(client):
    with patch('backend.routes.graph_routes.graph_agent') as mock_agent:
        mock_agent.get_post_graph.return_value = {"nodes": [], "links": []}
        
        response = await client.get('/post-graph/nonexistent_post')
        
        assert response.status_code == 404

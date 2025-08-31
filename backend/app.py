# backend/app.py
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from routes.graph_routes import graph_bp
from services.neo4j_service import neo4j_service
import asyncio # Required for async Flask routes

app = Flask(__name__)
CORS(app) # Enable CORS for all origins, adjust in production

# Load configuration
app.config.from_object(Config)

# Register Blueprints
app.register_blueprint(graph_bp, url_prefix='/api/graph')

# Error handling
@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad Request", "message": str(error)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not Found", "message": str(error)}), 404

@app.errorhandler(500)
def internal_server_error(error):
    app.logger.exception(f"An internal server error occurred: {error}")
    return jsonify({"error": "Internal Server Error", "message": str(error)}), 500

@app.before_request
def before_request():
    # Example: you could add authentication checks here
    pass

@app.teardown_appcontext
def teardown_db(exception=None):
    # Ensure Neo4j driver is closed when app context tears down
    if neo4j_service._driver:
        # In a multi-threaded/async environment, ensure close is safe
        # For simplicity with the singleton, we'll keep it here, but
        # consider managing driver lifecycle more carefully in very large apps.
        pass # The singleton handles its own connection lifecycle.

@app.route('/')
def home():
    return jsonify({"message": "GraphRAG Backend API is running!", "version": "1.0.0"})

# Ensure async routes work (Flask 2.0+ required)
# If you are on an older Flask version, you'll need to use async with a WSGI server like Gunicorn + Uvicorn worker
# For development: flask --app app run --debug --no-reload
if __name__ == '__main__':
    # Initialize Neo4j service at startup to verify connection
    try:
        neo4j_service.get_driver()
        app.logger.info("Neo4j service initialized successfully at app startup.")
    except ConnectionError:
        app.logger.error("Failed to initialize Neo4j service at startup. Check credentials.")

    # In development, run directly. For production, use Gunicorn/Uvicorn.
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5000)
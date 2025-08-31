# backend/agents/dataset_loader.py
from datasets import load_dataset, Dataset
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatasetLoader:
    def __init__(self):
        self.hf_token = Config.HUGGINGFACE_TOKEN

    def load_hf_dataset(self, dataset_name: str, config_name: str = None, split: str = 'train') -> Dataset:
        """
        Loads a dataset from Hugging Face.
        """
        try:
            if config_name:
                dataset = load_dataset(dataset_name, config_name, split=split, token=self.hf_token)
            else:
                dataset = load_dataset(dataset_name, split=split, token=self.hf_token)
            logger.info(f"Loaded Hugging Face dataset: {dataset_name} (split: {split}) with {len(dataset)} examples.")
            return dataset
        except Exception as e:
            logger.error(f"Failed to load Hugging Face dataset '{dataset_name}': {e}")
            raise

# Global instance
dataset_loader = DatasetLoader()
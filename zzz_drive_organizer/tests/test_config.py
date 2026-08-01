import os
import sys
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from utils.config_loader import ConfigLoader
    loader = ConfigLoader("config.yml")
    print("ConfigLoader loaded successfully!")
    print("Global settings:", loader.global_settings)
except Exception as e:
    print("Error loading ConfigLoader:")
    traceback.print_exc()

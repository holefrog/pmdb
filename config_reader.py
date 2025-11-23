import configparser
import os

def read_config(config_file="config.ini"):
    """Reads configuration from config.ini and validates the DeepL API key."""
    config = configparser.ConfigParser()
    deepl_api_key = None
    
    if not os.path.exists(config_file):
        print(f"❌ Configuration file '{config_file}' not found. Please create it from 'config.ini.example' and fill in the API key.")
    else:
        try:
            config.read(config_file)
            if "DeepL_API" in config:
                deepl_api_key = config.get("DeepL_API", "API").strip()
                if deepl_api_key.startswith("<YOUR_DEEPL_API_KEY>"):
                    print("⚠️ DeepL API key in config.ini is the default placeholder. Please update it.")
                    deepl_api_key = None
                
        except configparser.Error as e:
            print(f"❌ Error reading configuration from {config_file}: {e}")
            deepl_api_key = None
        except Exception as e:
            print(f"❌ An unexpected error occurred while loading config: {e}")
            deepl_api_key = None
    
    if not deepl_api_key:
        print("❌ DeepL API key is missing or invalid. Exiting.")
        return None
        
    return {"deepl_api_key": deepl_api_key}

import os

llm_client = None

def get_llm_client():
    """ Returns the LLM connection object. """    
    global llm_client
    global prompt_cache
    # connection already established?
    if llm_client is not None:
        return llm_client
    # Azure connection? 
    if (os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT")):
        from openai import AzureOpenAI
        return AzureOpenAI( 
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"), # "2024-10-21",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "")
        )
    # OpenAI connection?
    elif (os.getenv("OPENAI_API_KEY")):
        from openai import OpenAI
        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    else:
        raise ValueError("No valid OpenAI API key or Azure OpenAI API key found in environment variables.")
    


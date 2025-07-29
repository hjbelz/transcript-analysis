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

        # We now using the new Azure OpenAI Responses API (July 2025 in preview)
        # This API allows us to parse the response directly into a JSON object.
        # See https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/responses?tabs=python-secure 
        from openai import OpenAI
        return OpenAI( 
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            base_url=os.getenv("AZURE_OPENAI_ENDPOINT", "") + "/openai/v1/",
            default_query={"api-version": "preview"}
        )

    # OpenAI connection?
    elif (os.getenv("OPENAI_API_KEY")):
        from openai import OpenAI
        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    else:
        raise ValueError("No valid OpenAI API key or Azure OpenAI API key found in environment variables.")
    


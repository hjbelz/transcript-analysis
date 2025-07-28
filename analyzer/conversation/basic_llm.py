import os
import json
import pandas as pd
from pydantic import BaseModel
import chevron

from analyzer.conversation.basic import transcript_to_pseudo_xml
import filter

# module variable to cache the prompt definitions
prompt_cache = {}


def load_prompt_template(file_path, data=None):
    """ 
    Load a prompt from file or cache and return its content. 
    Optionally apply data to the prompt template.

    Args:
        file_path (str): Path to the prompt file.
        data (dict, optional): Data to apply to the prompt template.
                               If provided, the template will be rendered with this data.
    Returns:
        str: The prompt template content, optionally rendered with data.
    """
    global prompt_cache
    prompt_template = ""

    if file_path in prompt_cache:
        # Prompt template from cache
        prompt_template = prompt_cache[file_path]
    else:
        # Check if the file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The prompt file {file_path} does not exist.")
        # Read the prompt template from file    
        with open(file_path, 'r', encoding='utf-8') as file:
            prompt_template = file.read()
        # Cache the prompt template
        prompt_cache[file_path] = prompt_template
    
    # Optionally apply data to the prompt template
    if data:
        return chevron.render(prompt_template, data)
    else:
        return prompt_template

def apply_prompt_to_text(llm_api_client, prompt_file_path, transcript_text, data=None):
    """ Apply the prompt to the given prompt file and return the response. """
    classifier_prompt = load_prompt_template(prompt_file_path, data=data)

    # Call the LLM service API with the loaded prompt and transcript text
    response = llm_api_client.chat.completions.create(
        model="gpt-4.1-mini", # Deployment name!
        messages=[
            {"role": "system", "content": classifier_prompt + transcript_text}
        ]
    )
    return response.choices[0].message.content.strip()

def apply_prompt_with_json_schema(llm_api_client, prompt_file_path, transcript_text, json_schema, data=None):
    """ Apply the prompt to the given prompt file and return the response as a JSON object. """
    classifier_prompt = load_prompt_template(prompt_file_path, data=data)

    # Call the LLM service API with the loaded prompt and transcript text
    response = llm_api_client.responses.parse(
        model="gpt-4.1",
        input=classifier_prompt + transcript_text,
        text_format=json_schema
    )

    json_response = response.output_parsed
    # todo: check for model refused to answer 
    return json_response
    

def apply_llm_prompt_for_text_result(llm_api_client, transcripts, globalResultDF, promptFilePath, resultColumn="llmPromptAnalysis", filters=[]):
    """ Analyze the transcripts using a prompt and adding the result to the global result DataFrame. """

    # Analyze each transcript with the prompt
    analysis_results = []
    for transcript in transcripts:
        if not filter.is_relevant_transcript(globalResultDF, transcript, filters):
            analysis_results.append("No analysis")
            continue
        # Apply the prompt to the transcript
        transcript_as_pseudo_xml = transcript_to_pseudo_xml(transcript)
        print(transcript_as_pseudo_xml)  # Debugging output
        llm_result = apply_prompt_to_text(llm_api_client, promptFilePath, transcript_as_pseudo_xml)
        analysis_results.append(llm_result)
        # break  # Remove this break to analyze all transcripts

    globalResultDF["llmPromptAnalysis"] = analysis_results


def apply_llm_prompt_for_JSON_result(llm_api_client, transcripts, globalResultDF, promptFilePath, jsonSchema, resultColumns={}, filters=[], data = None):
    """ Analyze the transcripts using a prompt and add the resulting JSON structure to the global result DataFrame. """
    # create result columns
    analysis_results = {}
    for key in resultColumns.keys():
        analysis_results[resultColumns[key]] = []

    # Analyze each transcript with the prompt
    for transcript in transcripts:
        if not filter.is_relevant_transcript(globalResultDF, transcript, filters):
            for key in resultColumns.keys():
                analysis_results[resultColumns[key]].append("No analysis")
            continue
        # Apply the prompt to the transcript
        transcript_as_pseudo_xml = transcript_to_pseudo_xml(transcript)
        print(transcript_as_pseudo_xml)  # Debugging output

        llm_result_json = apply_prompt_with_json_schema(llm_api_client, promptFilePath, transcript_as_pseudo_xml, jsonSchema, data=data)
        print(llm_result_json)  # Debugging output

        # Extract the results from the JSON response
        for result_key in resultColumns.keys():
            analysis_results[resultColumns[result_key]].append(getattr(llm_result_json, result_key, "No result"))
        # break  # Remove this break to analyze all transcripts
    
    # Add the results to the global DataFrame
    for key in resultColumns.keys():
        globalResultDF[resultColumns[key]] = analysis_results[resultColumns[key]]




class CategorizeTranscriptsJson(BaseModel):
    """ Pydantic model for the JSON schema of transcript categorization. """
    topic: str
    intent: str
    breakdown: str

def categorize_transcripts(llm_api_client, transcripts, globalResultDF, categories_file=None):
    """ Categorize transcripts using LLM and add the results to the global DataFrame. """
    # Load the category list if provided
    categories = None
    if categories_file:
        if not os.path.exists(categories_file):
            raise FileNotFoundError(f"The categories file {categories_file} does not exist.")
        with open(categories_file, 'r', encoding='utf-8') as file:
            categories = file.read()

    if categories:
        # Closed categorization with predefined categories
        apply_llm_prompt_for_JSON_result(llm_api_client, transcripts, globalResultDF, "./analyzer/conversation/llm_prompts/prmt_topic_and_intent_closed.md", CategorizeTranscriptsJson, resultColumns={"topic": "topic", "intent": "intent", "breakdown": "breakdown"}, filters=[filter.filter_no_user_utterance], data={"category_list": categories})
    else:
        # Open categorization
        apply_llm_prompt_for_JSON_result(llm_api_client, transcripts, globalResultDF, "./analyzer/conversation/llm_prompts/prmt_topic_and_intent_open.md", CategorizeTranscriptsJson, resultColumns={"topic": "topic", "intent": "intent", "breakdown": "breakdown"}, filters=[filter.filter_no_user_utterance])


class AssessSentimentJson(BaseModel):
    """ Pydantic model for the JSON schema of sentiment analysis. """
    sentiment_label: str
    reason: str
    utterance: str

def assess_sentiment(llm_api_client, transcripts, globalResultDF):
    """ Assess sentiment of transcripts using LLM and add the results to the global DataFrame. """
    apply_llm_prompt_for_JSON_result(llm_api_client, transcripts, globalResultDF, "./analyzer/conversation/llm_prompts/prmt_sentiment_analysis.md", AssessSentimentJson, resultColumns={"sentiment_label": "Sentiment", "reason": "Reason", "utterance": "Characteristic utterance"}, filters=[filter.filter_no_user_utterance])

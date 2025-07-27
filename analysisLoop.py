import pandas as pd
import json
import os

import analyzer.conversation.basic
import analyzer.conversation.basic_llm
import filter
import llm_client


def readTranscriptFile(filePath):
    """ Reads a transcript file and returns its content as a JSON object. """

    # Read the JSON file
    with open(filePath, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Validate the JSON structure
    if not isinstance(data, dict) or "conversation" not in data or "utterances" not in data["conversation"] or not isinstance(data["conversation"]["utterances"], list) or "sessionId" not in data["conversation"]:
        raise ValueError("Invalid JSON structure in the transcript file.")

    return data


def readTranscriptFilesInPath(path):
    """ Read transcript files in the given path into a array of JSON objects. """

    # Check if the path exists
    if not os.path.exists(path):
        raise FileNotFoundError(f"The path {path} does not exist.")
    
    # Iterate through all files in the directory
    transcripts = []
    with os.scandir(path) as iterator:
        for entry in iterator:
            if entry.name.endswith('.json') and entry.is_file():
                jsonTranscript = readTranscriptFile(entry.path)
                transcripts.append(jsonTranscript)

    print(f"Read {len(transcripts)} transcript files from {path}.")
    return transcripts


def initGlobalResultDataFrameFromTranscripts(transcripts):
    """ Initialize a global DataFrame with the meta data from the given transcripts. """

    # Create a global DataFrame for the list of transcripts
    df = pd.DataFrame()

    sessionIds = []

    for transcript in transcripts:
        sessionIds.append(transcript["conversation"]["sessionId"])

    df["sessionId"] = sessionIds
    return df


if(__name__ == "__main__"):
    # 
    # Test Script for the analysis loop
    #

    # read transcript files from the given path
    transcripts = readTranscriptFilesInPath("./transcripts")

    # initialize global result DataFrame
    globalResultDF = initGlobalResultDataFrameFromTranscripts(transcripts)
    
    # perform global analysis
    analyzer.conversation.basic.countTurnsInTranscripts(transcripts, globalResultDF, True)
    analyzer.conversation.basic.maxWordCountUserUtterances(transcripts, globalResultDF)
    # analyzer.conversation.basic.addLocalPath(transcripts, globalResultDF)

    # apply LLM prompt analysis
    llm_api_client = llm_client.get_llm_client()
    analyzer.conversation.basic_llm.categorize_transcripts(llm_api_client, transcripts, globalResultDF)
    
    # experimental LLM prompt analysis
    #analyzer.conversation.basic_llm.apply_llm_prompt_for_JSON_result(llm_api_client, transcripts, globalResultDF, "first-utterance-classifier-prompt.txt", resultColumns={"Opening Action": "Opening Action", "Request Category": "Request Category", "Ambiguity": "Ambiguity"}, filters=[filter.filter_no_user_utterance])


    # finally, add the transcript content to the global result DataFrame
    analyzer.conversation.basic.addTranscriptsToResult(transcripts, globalResultDF)

    # Save the global result DataFrame to a file
    # globalResultDF.to_csv("./results/globalResult.csv", index=False)
    globalResultDF.to_excel("./results/globalResult.xlsx", index=False)

    print(globalResultDF)
 
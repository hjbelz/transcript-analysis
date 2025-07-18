import pandas as pd
import json
import os


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

def globAnalysis_countTurnsInTranscripts(transcripts, globalResultDF, isAggregation=False):
    """ Count the number of turns in the given transcripts and add a row for each to the global result. """

    turnCounts = []
    for transcript in transcripts:
        count = 0
        lastTurnRole = None
        iterator = iter(transcript["conversation"]["utterances"])
        nextUtterance = next(iterator, None)
        while (nextUtterance is not None):
            # When aggregating: Only if the role is different from the last one, we count it as a new turn
            if not isAggregation or nextUtterance["role"] != lastTurnRole:
                count += 1
                lastTurnRole = nextUtterance["role"]
            # Move to the next utterance
            nextUtterance = next(iterator, None)
        # Add transcript-level turn count to the list
        turnCounts.append(count)

    globalResultDF["turnCount"] = turnCounts

def globAnalysis_addLocalPath(transcripts, globalResultDF):
    """ Add the local path of the transcript files to the global result DataFrame (only works for CSV export). """
    localPaths = []
    for transcript in transcripts:
        localPaths.append("file://" + os.getcwd() + "/build/" + transcript["conversation"]["sessionId"] + ".json")

    globalResultDF["localPath"] = localPaths

def globAnalysis_maxWordCountUserUtterances(transcripts, globalResultDF):
    """ Calculate the maximum word count of user utterances in the transcripts. """
    maxWordCounts = []
    for transcript in transcripts:
        maxCount = 0
        for utterance in transcript["conversation"]["utterances"]:
            if utterance["role"] == "user":
                wordCount = len(utterance["content"].split())
                if wordCount > maxCount:
                    maxCount = wordCount
        maxWordCounts.append(maxCount)

    globalResultDF["maxUserWordCount"] = maxWordCounts

def globAnalysis_LLMPrompt(transcripts, globalResultDF, promptFilePath, resultColumnName="llmPromptAnalysis"):
    """ Analyze the transcripts using a prompt and adding the result to the global result DataFrame. """

    
    # Analyze each transcript with the prompt
    analysisResults = []
    for transcript in transcripts:
        # Here you would implement the actual analysis logic using the prompt
        # For demonstration, we'll just return the prompt length
        analysisResults.append(len(prompt))

    globalResultDF["llmPromptAnalysis"] = analysisResults

# read transcript files from the given path
transcripts = readTranscriptFilesInPath("./transcripts")

# initialize global result DataFrame
globalResultDF = initGlobalResultDataFrameFromTranscripts(transcripts)
globAnalysis_countTurnsInTranscripts(transcripts, globalResultDF, True)
# globAnalysis_addLocalPath(transcripts, globalResultDF)
globAnalysis_maxWordCountUserUtterances(transcripts, globalResultDF)

# globalResultDF.to_csv("./build/globalResult.csv", index=False)
globalResultDF.to_excel("./transcripts/globalResult.xlsx", index=False)

print(globalResultDF)

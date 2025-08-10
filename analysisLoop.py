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


def read_list_of_transcript_files(transcript_filenames):
    """ Reads multiple transcript files and returns their content as a list of JSON objects. """
    transcripts = []
    for filename in transcript_filenames:
        try:
            transcript = readTranscriptFile(filename)
            transcripts.append(transcript)
        except Exception as e:
            print(f"Error reading transcript file {filename}: {e}")
    
    return transcripts





def compileTranscriptFileListInPath(path):
    """ Compile a list of transcript files in the given path. """
    # Check if the path exists
    if not os.path.exists(path):
        raise FileNotFoundError(f"The path {path} does not exist.")

    # Iterate through all files in the directory
    transcript_files = []
    with os.scandir(path) as iterator:
        for entry in iterator:
            if entry.name.endswith('.json') and entry.is_file():
                transcript_files.append(entry.path)

    print(f"Found {len(transcript_files)} transcript files in {path}.")
    return transcript_files









def initResultDataFrameFromTranscripts(transcripts):
    """ Initialize a DataFrame with the meta data from the given transcripts. """

    # Create a DataFrame for the list of transcripts
    df = pd.DataFrame()

    sessionIds = []

    for transcript in transcripts:
        sessionIds.append(transcript["conversation"]["sessionId"])

    df["sessionId"] = sessionIds
    return df


def readProcessedFiles(file_path):
    """ Read the list of already processed files from a log file. """
    if not os.path.exists(file_path):
        print(f"Processed files log {file_path} does not exist. Starting fresh.")
        open(file_path, 'w').close()
        return []
    
    with open(file_path, 'r', encoding='utf-8') as file:
        processed_files = [line.strip() for line in file.readlines()]
    
    return processed_files



if(__name__ == "__main__"):
    # 
    # Test Script for the analysis loop
    #

    # Compile the list of transcript files in the given path not processed yet 
    allTranscriptFilesInPath = compileTranscriptFileListInPath("./transcripts")
    alreadyProcessedFiles = readProcessedFiles("./results/processedFiles.log")
    transcriptFilesToProcess = list(set(allTranscriptFilesInPath) - set(alreadyProcessedFiles))

    # TODO : Process batches of n files
    batch_size = 5
    nextBatchOfTranscriptFilenames = transcriptFilesToProcess[:batch_size]  # Adjust the batch size as needed
    # read transcript files from the given path
    transcripts = read_list_of_transcript_files(nextBatchOfTranscriptFilenames)

    # initialize result DataFrame
    resultDF = initResultDataFrameFromTranscripts(transcripts)

    # Append the batch results in the dataframe to the result
    with pd.ExcelWriter('./results/globalResult.xlsx', engine='openpyxl', mode='a', if_sheet_exists="replace") as writer:
        resultDF.to_excel(writer, sheet_name='Results', index=False)
    
    # Save the processed files to the log file
    with open("./results/processedFiles.log", 'a', encoding='utf-8') as file:
        for filename in nextBatchOfTranscriptFilenames:
            file.write(f"{filename}\n") 

    print(f"Processing {len(nextBatchOfTranscriptFilenames)} transcript files: {nextBatchOfTranscriptFilenames}")

    # TODO: Always write the result DataFrame to a SQLlite database. When all files are processed, the database can be exported to an Excel file.
    



    # end execution
    import sys
    sys.exit(0)



    # initialize global result DataFrame
    resultDF = initResultDataFrameFromTranscripts(transcripts)

    # read transcript files from the given path
    # transcripts = readTranscriptFilesInPath("./transcripts")

    # initialize global result DataFrame
    # globalResultDF = initGlobalResultDataFrameFromTranscripts(transcripts)
    
    # perform global analysis
    analyzer.conversation.basic.countTurnsInTranscripts(transcripts, resultDF, True)
    analyzer.conversation.basic.maxWordCountUserUtterances(transcripts, resultDF)
    # analyzer.conversation.basic.addLocalPath(transcripts, globalResultDF)

    # apply LLM prompt analysis
    llm_api_client = llm_client.get_llm_client()
    # LLM : Categorization (closed categories)
    analyzer.conversation.basic_llm.categorize_transcripts(llm_api_client, transcripts, resultDF, categories_file="./category_list-energy dso.json")
    # LLM : Categorization (open categories)
    # analyzer.conversation.basic_llm.categorize_transcripts(llm_api_client, transcripts, globalResultDF)
    # LLM : Sentiment Analysis
    analyzer.conversation.basic_llm.assess_sentiment(llm_api_client, transcripts, resultDF)

    # experimental LLM prompt analysis
    #analyzer.conversation.basic_llm.apply_llm_prompt_for_JSON_result(llm_api_client, transcripts, globalResultDF, "first-utterance-classifier-prompt.txt", resultColumns={"Opening Action": "Opening Action", "Request Category": "Request Category", "Ambiguity": "Ambiguity"}, filters=[filter.filter_no_user_utterance])


    # finally, add the transcript content to the global result DataFrame
    analyzer.conversation.basic.addTranscriptsToResult(transcripts, resultDF)

    # Save the global result DataFrame to a file
    # globalResultDF.to_csv("./results/globalResult.csv", index=False)
    resultDF.to_excel("./results/globalResult.xlsx", index=False)

    print(resultDF)
 
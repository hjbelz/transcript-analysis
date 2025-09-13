""" Main Module for Transcript Analysis
"""
from datetime import datetime
import json
import os
import pandas as pd
from sqlalchemy import create_engine

import analyzer.conversation.basic
import analyzer.conversation.basic_llm
import llm_client

# global options (to be paramters for the CLI)
result_path = "./results"
transcript_path = "./transcripts"
batch_size = 5  # Number of transcript files to process in one batch


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


def initGlobalResultPersistence(path):
    """ Create SQLAlchemy engine for global result persistence. """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Cannot create/access database in path {path}.")

    # Initialize SQLite database in path
    database_file = os.path.join(path, "results.db")
    engine = create_engine(f'sqlite:///{database_file}')
    return engine


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


def create_final_report(database_engine, output_path):
    """
    Read all results from database and create a final Excel report.

    Args:
        database_engine: SQLAlchemy database engine
        output_path: Path where the Excel report should be saved
    """
    with database_engine.connect() as connection:
        complete_resultsDF = pd.read_sql('transcripts', con=connection)
        complete_resultsDF.to_excel(output_path, index=False)
        print(f"Final report saved to {output_path}")


if(__name__ == "__main__"):
    # 
    # Main analysis loop
    #

    # Compile the list of transcript files in the given path not processed yet 
    allTranscriptFilesInPath = compileTranscriptFileListInPath(transcript_path)
    alreadyProcessedFiles = readProcessedFiles(os.path.join(result_path, "processedFiles.log"))
    transcriptFilesToProcess = list(set(allTranscriptFilesInPath) - set(alreadyProcessedFiles))
    print(f"{len(transcriptFilesToProcess)} transcript files still to process.")

    database_engine = initGlobalResultPersistence(result_path)

    #
    # Analysis loop: Process batches of transcript files
    #
    while (transcriptFilesToProcess):
        nextBatchOfTranscriptFilenames = transcriptFilesToProcess[:batch_size]  # Adjust the batch size as needed
        
        # read transcript files from the given path
        transcripts = read_list_of_transcript_files(nextBatchOfTranscriptFilenames)

        # initialize result DataFrame
        resultDF = initResultDataFrameFromTranscripts(transcripts)

        # Basic global analysis
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

        # Append the batch results to the database
        with database_engine.connect() as connection:
            resultDF.to_sql('transcripts', con=connection, if_exists='append', index=False)
            connection.commit()
            print(f"Appended {len(resultDF)} records to the database.")
        
        # Save the processed files to the log file
        with open("./results/processedFiles.log", 'a', encoding='utf-8') as file:
            for filename in nextBatchOfTranscriptFilenames:
                file.write(f"{filename}\n") 

        # Remove processed files from the list
        transcriptFilesToProcess = transcriptFilesToProcess[batch_size:]

        print(f"Processed {len(nextBatchOfTranscriptFilenames)} transcript files: {nextBatchOfTranscriptFilenames}")

    # After processing all files, create the final report in Excel format
    create_final_report(database_engine, output_path=os.path.join(result_path, f"results-{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"))
    print(f"Completed processing of {len(allTranscriptFilesInPath)} transcript files at {datetime.now().isoformat()}.")

    # Close the database connection
    database_engine.dispose()

 
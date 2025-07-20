import pandas as pd

def is_relevant_transcript(globalResultDF: pd.DataFrame, transcript: dict, filter_functions: list) -> bool:
    """
    Filters the transcripts based on the provided criteria.
    
    Args:
        df_transcript_row (pd.Series): A row from the DataFrame containing transcript metadata.
        filter_functions (list): List of filter functions to apply.

    Returns:
        bool: True if the transcript is relevant, False otherwise.
    """
    if not isinstance(filter_functions, list):
        raise ValueError("filter_functions must be a list of functions.")

    df_transcript_row = globalResultDF[globalResultDF["sessionId"] == transcript["conversation"]["sessionId"]].iloc[0]
    if df_transcript_row.empty:
        raise ValueError("No matching transcript found.")

    for func in filter_functions:
        if not func(transcript, df_transcript_row):
            return False
    return True 


def filter_no_user_utterance(transcript: dict, df_transcript_row: pd.Series) -> bool:
    """
    Filter function to exclude transcripts with no user utterances.
    
    Args:
        df_transcript_row (pd.Series): A row from the DataFrame containing transcript metadata.

    Returns:
        bool: True if the transcript has user utterances, False otherwise.
    """
    maxUserWordCount = df_transcript_row.get("maxUserWordCount", 0)
    print (f"Checking if maxUserWordCount > 0: {maxUserWordCount}")
    return maxUserWordCount > 0

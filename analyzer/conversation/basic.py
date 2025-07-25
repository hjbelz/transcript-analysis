import os


def transcript_to_pseudo_xml(transcript):
    """ Helper function: Convert a transcript to a pseudo XML format for LLM processing. """
    utterances = transcript["conversation"]["utterances"]
    xml_content = "<conversation>\n"
    for utterance in utterances:
        role = utterance["role"]
        content = utterance["content"] # utterance["content"].replace("<", "&lt;").replace(">", "&gt;")
        xml_content += f"  <{role}>{content}</{role}>\n"
    xml_content += "</conversation>"
    return xml_content


def countTurnsInTranscripts(transcripts, globalResultDF, isAggregation=False):
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


def maxWordCountUserUtterances(transcripts, globalResultDF):
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

def addLocalPath(transcripts, globalResultDF):
    """ Add the local path of the transcript files to the global result DataFrame (only works for CSV export). """
    localPaths = []
    for transcript in transcripts:
        localPaths.append("file://" + os.getcwd() + "/build/" + transcript["conversation"]["sessionId"] + ".json")

    globalResultDF["localPath"] = localPaths


def addTranscriptsToResult(transcripts, globalResultDF):
    """Adds the transcript content to the dataframe for reference."""
    transcripts_as_pseudo_xml = []
    for transcript in transcripts:
        transcripts_as_pseudo_xml.append(transcript_to_pseudo_xml(transcript))

    globalResultDF["transcript"] = transcripts_as_pseudo_xml
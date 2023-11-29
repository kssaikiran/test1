# general imports
import os
import yaml
import json

# import azure service wrappers
from cxo_chat.services.auth import Auth
from cxo_chat.services.azureOpenAI import AzureOpenAI
from cxo_chat.services.cosmosDB import CosmosDB
from cxo_chat.services.microsoftGraph import MicrosoftGraph

# import genai modules
from cxo_chat.genai.grounding import Grounding
from cxo_chat.genai.functions import Functions
from cxo_chat.genai.chat import Chat

# import streamlist
import streamlit as st

# SET UP CONFIGURATION

# read yaml config file
with open('../config.yaml') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

# set up
os.environ['OPENAI_API_KEY'] = config['AzureOpenAI']['AZURE_API_KEY']
os.environ["OPENAI_API_TYPE"] = config['AzureOpenAI']['AZURE_API_TYPE']
os.environ["OPENAI_API_BASE"] = config['AzureOpenAI']['AZURE_API_BASE']
os.environ["OPENAI_API_VERSION"] = config['AzureOpenAI']['AZURE_API_VERSION']

# authentication
auth = Auth(config)
auth.fake_login()

# initialize the Azure service wrappers
azure_openai = AzureOpenAI(config)  # currently does not requere auth as it works on static cred
cosmos_db = CosmosDB(config, auth)
microsoft_graph = MicrosoftGraph(config, auth)

# package the services
azure_services = {
    "azure_openai": azure_openai,
    "cosmos_db": cosmos_db,
    "microsoft_graph": microsoft_graph
}

# initialize grounding
grounding = Grounding(config, azure_services)

# initialize functions and chat
callback_function_services = {
    "microsoft_graph": microsoft_graph,
    "grounding": grounding
}
functions = Functions(config, callback_function_services)
chat = Chat(config, functions)


#  GUI CONFIGURATION

st.title("Echo Bot")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Send a message"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # run the user message
    response_message = chat.run(user_message=prompt)

    # check if function call is necessary
    if response_message.get("function_call"):
        with st.status("Getting relevant data...", expanded=True) as status:

            # Check if the model wants to call a function
            callback_count = 0
            while callback_count < config['GenAI']['MAX_CALLBACKS'] and \
                    response_message.get("function_call"):

                # increment callback count
                callback_count += 1

                # extract function name and parameters
                function_name = response_message["function_call"]["name"]

                # print message to ui
                match function_name:
                    case "get_full_context":
                        st.write('Getting full context...')
                    case "get_email_context":
                        st.write('Getting email context...')
                    case "get_file_context":
                        st.write('Getting file context...')
                    case "get_calendar_events_in_period":
                        st.write('Getting calendar events in period...')
                    case "get_next_calendar_event":
                        st.write('Getting next calendar event...')
                    case "get_calendar_events_from_today":
                        st.write('Getting calendar events for today...')
                    case "search_calendar_event":
                        st.write('Searching calendar events...')
                    case _:
                        st.write('UI for this function callback is not implemented...')

                params = json.loads(response_message["function_call"]["arguments"])

                # run function
                function_response = chat.functions.run_function(function_name, params)

                # Add the assistant response and function response to the messages
                chat.messages.append({
                    "role": response_message["role"],
                    "function_call": {
                        "name": function_name,
                        "arguments": response_message["function_call"]["arguments"],
                    },
                    "content": None
                })

                # Add function response to the messages
                chat.messages.append({
                    "role": "function",
                    "name": function_name,
                    "content": function_response,
                })

                # llm call
                response_message = chat.call_llm()

            # check if successful:
            if 'content' in response_message:

                # Add the assistant response to the messages
                chat.messages.append({
                    "role": response_message["role"],
                    "content": response_message.content
                })

                print(json.dumps(chat.messages, indent=4))

                # extract response
                response = response_message["content"]
                status.update(label="Revent data was found", state="complete", expanded=False)

            else:
                response = 'Sorry, I could not find relevant data'
                status.update(label="Revent data was not found", state="complete", expanded=False)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

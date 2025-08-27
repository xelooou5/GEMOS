from flask import Flask, request, jsonify
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/slack/events', methods=['POST'])
def slack_events():
    data = request.get_json()
    
    # Handle challenge verification
    if data and data.get('type') == 'url_verification':
        return data['challenge']
    
    # Handle events
    if data and data.get('type') == 'event_callback':
        event = data.get('event', {})
        event_type = event.get('type')
        
        if event_type == 'app_mention':
            handle_mention(event)
        elif event_type == 'message':
            handle_message(event)
        elif event_type == 'reaction_added':
            handle_reaction(event)
        elif event_type == 'file_shared':
            handle_file(event)
    
    return 'OK'

def handle_mention(event):
    text = event.get('text', '')
    user = event.get('user')
    logging.info(f'GEM mentioned by {user}: {text}')

def handle_message(event):
    text = event.get('text', '')
    user = event.get('user')
    logging.info(f'Message from {user}: {text}')

def handle_reaction(event):
    reaction = event.get('reaction')
    user = event.get('user')
    logging.info(f'Reaction {reaction} from {user}')

def handle_file(event):
    file_id = event.get('file_id')
    user = event.get('user_id')
    logging.info(f'File {file_id} shared by {user}')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3002)
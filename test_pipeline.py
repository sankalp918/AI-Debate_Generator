import requests
import time
import json


def test_pipeline():
    # Test text generation
    print("Testing text generation...")
    response = requests.post('http://localhost:8001/generate', json={
        'topic': 'Artificial Intelligence in Healthcare',
        'position': 'pro',
        'context': ''
    })
    print(f"Text Gen: {response.status_code}")

    # Test TTS
    print("Testing TTS...")
    response = requests.post('http://localhost:8002/synthesize', json={
        'text': 'Hello, this is a test of the text to speech system.',
        'speaker': 'person1'
    })
    print(f"TTS: {response.status_code}")

    # Full pipeline test
    print("Testing full pipeline...")
    response = requests.post('http://localhost:8000/generate', json={
        'topic': 'AI will improve healthcare outcomes',
        'rounds': 1
    })
    print(f"Full Pipeline: {response.status_code}")


if __name__ == '__main__':
    test_pipeline()
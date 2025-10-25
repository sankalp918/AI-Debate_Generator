import requests
import time
import json
import sys


def test_text_generation():
    """Test the text generation service"""
    print("\n" + "="*50)
    print("Testing Text Generation Service...")
    print("="*50)

    try:
        response = requests.post(
            'http://localhost:8001/generate',
            json={
                'topic': 'Artificial Intelligence in Healthcare',
                'position': 'pro',
                'context': ''
            },
            timeout=300
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Text Generation Service: PASSED")
            print(f"Generated text preview: {data.get('text', '')[:100]}...")
            return True
        else:
            print(f"✗ Text Generation Service: FAILED")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"✗ Text Generation Service: CONNECTION FAILED")
        print("  Make sure the service is running on port 8001")
        return False
    except Exception as e:
        print(f"✗ Text Generation Service: ERROR - {e}")
        return False


def test_tts():
    """Test the text-to-speech service"""
    print("\n" + "="*50)
    print("Testing Text-to-Speech Service...")
    print("="*50)

    try:
        response = requests.post(
            'http://localhost:8002/synthesize',
            json={
                'text': 'Hello, this is a test of the text to speech system.',
                'speaker': 'person1'
            },
            timeout=300
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print(f"✓ TTS Service: PASSED")
            print(f"Audio file size: {len(response.content)} bytes")
            return True
        else:
            print(f"✗ TTS Service: FAILED")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"✗ TTS Service: CONNECTION FAILED")
        print("  Make sure the service is running on port 8002")
        return False
    except Exception as e:
        print(f"✗ TTS Service: ERROR - {e}")
        return False


def test_orchestrator_health():
    """Test if orchestrator service is accessible"""
    print("\n" + "="*50)
    print("Testing Orchestrator Service...")
    print("="*50)

    try:
        response = requests.get('http://localhost:8000/', timeout=30)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print(f"✓ Orchestrator Service: ACCESSIBLE")
            return True
        else:
            print(f"✗ Orchestrator Service: FAILED")
            return False

    except requests.exceptions.ConnectionError:
        print(f"✗ Orchestrator Service: CONNECTION FAILED")
        print("  Make sure the service is running on port 8000")
        return False
    except Exception as e:
        print(f"✗ Orchestrator Service: ERROR - {e}")
        return False


def test_full_pipeline_with_colab(colab_url=None):
    """Test the complete debate generation pipeline"""
    print("\n" + "="*50)
    print("Testing Full Pipeline...")
    print("="*50)

    if not colab_url:
        print("⚠ SKIPPING: Full pipeline test requires Colab URL")
        print("  To test the full pipeline, provide a Colab ngrok URL:")
        print("  python test_pipeline.py --colab-url https://xxxx.ngrok.io")
        return None

    try:
        print(f"Using Colab URL: {colab_url}")
        print("⚠ This may take several minutes...")

        response = requests.post(
            'http://localhost:8000/generate',
            json={
                'topic': 'AI will improve healthcare outcomes',
                'rounds': 1,
                'colab_url': colab_url
            },
            timeout=600  # 10 minutes timeout for full pipeline
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✓ Full Pipeline: PASSED")
                print(f"Video saved to: {data.get('video_path')}")
                return True
            else:
                print(f"✗ Full Pipeline: FAILED")
                print(f"Error: {data.get('error')}")
                return False
        else:
            print(f"✗ Full Pipeline: FAILED")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print(f"✗ Full Pipeline: TIMEOUT")
        print("  The request took too long. This might be normal for video generation.")
        return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Full Pipeline: CONNECTION FAILED")
        print("  Make sure the orchestrator is running on port 8000")
        return False
    except Exception as e:
        print(f"✗ Full Pipeline: ERROR - {e}")
        return False


def test_pipeline(colab_url=None):
    """Run all pipeline tests"""
    print("\n" + "🎬 AI Debate Generator - Pipeline Testing")
    print("=" * 50)

    results = {
        'text_generation': test_text_generation(),
        'tts': test_tts(),
        'orchestrator': test_orchestrator_health(),
    }

    # Only test full pipeline if Colab URL is provided
    if colab_url:
        results['full_pipeline'] = test_full_pipeline_with_colab(colab_url)
    else:
        print("\n" + "="*50)
        print("⚠ Skipping Full Pipeline Test")
        print("="*50)
        print("To test the complete pipeline with video generation:")
        print("1. Start SadTalker on Google Colab (SadTalker_Colab.ipynb)")
        print("2. Get the ngrok URL from Colab")
        print("3. Run: python test_pipeline.py --colab-url https://your-ngrok-url.ngrok.io")

    # Print summary
    print("\n" + "="*50)
    print("📊 Test Summary")
    print("="*50)

    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASSED" if result is True else ("✗ FAILED" if result is False else "⊘ SKIPPED")
        print(f"{test_name.replace('_', ' ').title()}: {status}")

    print(f"\nTotal: {total} tests | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")

    if failed > 0:
        print("\n⚠ Some tests failed. Please check the services are running:")
        print("  docker-compose up --build")
        return 1
    elif skipped > 0 and not colab_url:
        print("\n✓ All available tests passed!")
        print("  Note: Full pipeline test was skipped (requires Colab URL)")
        return 0
    else:
        print("\n✓ All tests passed successfully!")
        return 0


if __name__ == '__main__':
    # Parse command line arguments
    colab_url = None
    if len(sys.argv) > 1:
        if '--colab-url' in sys.argv:
            try:
                idx = sys.argv.index('--colab-url')
                colab_url = sys.argv[idx + 1]
            except IndexError:
                print("Error: --colab-url requires a URL argument")
                print("Usage: python test_pipeline.py --colab-url https://your-ngrok-url.ngrok.io")
                sys.exit(1)
        elif '--help' in sys.argv or '-h' in sys.argv:
            print("AI Debate Generator - Pipeline Testing")
            print("\nUsage:")
            print("  python test_pipeline.py                  # Test individual services")
            print("  python test_pipeline.py --colab-url URL  # Test with full pipeline")
            print("\nOptions:")
            print("  --colab-url URL    Colab ngrok URL for SadTalker service")
            print("  --help, -h         Show this help message")
            sys.exit(0)

    exit_code = test_pipeline(colab_url)
    sys.exit(exit_code)

# Updated text-generation/text_generator.py
from flask import Flask, request, jsonify
import requests
import json
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

LM_STUDIO_URL = "http://host.docker.internal:1234/v1/chat/completions"


def generate_debate_content(topic, position, previous_context=""):
    """Generate debate content with proper LM Studio response handling"""

    # Try LM Studio first
    try:
        prompt = f"""Debate Topic: {topic}

You are arguing {'FOR' if position == 'pro' else 'AGAINST'} this statement.

Provide a compelling 2-3 sentence argument. Be specific and persuasive. Keep under 150 words.

Your argument:"""

        payload = {
            "model": "openai-gpt-oss-20b-abliterated-uncensored-neo-imatrix",
            "messages": [
                {"role": "system", "content": "You are a skilled debater. Provide clear, concise arguments."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 200,
            "stream": False
        }

        logging.info(f"Sending LM Studio request for {position} position")
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=6000)

        if response.status_code == 200:
            result = response.json()
            logging.info(f"LM Studio response: {result}")

            # Handle different response structures
            content = ""
            if 'choices' in result and len(result['choices']) > 0:
                choice = result['choices'][0]

                # Check message content
                if 'message' in choice and 'content' in choice['message']:
                    content = choice['message']['content'].strip()

                # Check if content is in reasoning field (some models use this)
                elif 'message' in choice and 'reasoning' in choice['message']:
                    reasoning = choice['message']['reasoning'].strip()
                    if reasoning and len(reasoning) > 20:
                        # Extract argument from reasoning
                        lines = reasoning.split('\n')
                        for line in lines:
                            if 'sentence' in line.lower() and len(line) > 50:
                                content = line.strip()
                                break

                # Check direct text field
                elif 'text' in choice:
                    content = choice['text'].strip()

            # Validate content
            if content and len(content) > 20 and content != "...":
                logging.info(f"LM Studio success: {len(content)} chars")
                return content
            else:
                logging.warning(f"LM Studio returned invalid content: '{content}'")

        else:
            logging.error(f"LM Studio API error: {response.status_code}")

    except Exception as e:
        logging.error(f"LM Studio error: {e}")

    # Fallback to template responses
    logging.info("Using fallback text generation")
    return generate_fallback_content(topic, position)


def generate_fallback_content(topic, position):
    """Generate high-quality fallback content"""

    if position == 'pro':
        templates = [
            f"The transformation where {topic.lower()} represents an inevitable technological evolution that will ultimately benefit society. Historical evidence from the Industrial Revolution shows that while automation initially displaces workers, it creates new industries and higher-skilled employment opportunities. Companies like Tesla and Amazon demonstrate how automation reduces costs while generating entirely new job categories in robotics, AI development, and human-machine collaboration.",

            f"Economic data strongly supports that {topic.lower()} will drive unprecedented productivity gains. McKinsey research indicates that AI automation could contribute $13 trillion to global GDP by 2030 through increased efficiency and innovation. Countries embracing this transition, like Singapore and South Korea, are already seeing reduced workplace injuries, improved product quality, and new service sectors emerging around human creativity and emotional intelligence.",

            f"The technological capabilities now exist to make {topic.lower()} a reality within this timeframe. Recent advances in machine learning, robotics, and natural language processing have reached human-level performance in manufacturing, customer service, and data analysis. Companies that resist this transition will become uncompetitive, while early adopters create safer, more fulfilling work environments focused on uniquely human skills."
        ]
    else:
        templates = [
            f"The premise that {topic.lower()} fundamentally misunderstands the complexity of human work and the limitations of current AI systems. While automation excels at repetitive tasks, most jobs require emotional intelligence, creative problem-solving, and contextual judgment that remain beyond AI capabilities. The Oxford Economics study showing 20 million manufacturing jobs at risk fails to account for the 97 million new roles the World Economic Forum predicts AI will create.",

            f"Historical precedent suggests that {topic.lower()} overestimates the speed of technological adoption and underestimates human adaptability. The transition from agriculture to manufacturing took over a century, allowing gradual workforce adjustment. Current retraining programs and educational initiatives are already preparing workers for AI collaboration rather than replacement, as seen in Germany's Industry 4.0 initiative.",

            f"The assumption that {topic.lower()} ignores critical economic and social factors that will slow this transition. Regulatory frameworks, ethical concerns about algorithmic bias, and the high costs of AI implementation will create natural barriers. Additionally, consumer preferences often favor human interaction in healthcare, education, and hospitality sectors, ensuring sustained demand for human workers in these essential areas."
        ]

    # Use topic hash to select template for consistency
    template_index = hash(topic) % len(templates)
    return templates[template_index]


@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        topic = data.get('topic', '').strip()
        position = data.get('position', 'pro')
        context = data.get('context', '')

        if not topic:
            return jsonify({'error': 'No topic provided'}), 400

        logging.info(f"Generating content for: '{topic}' ({position})")

        content = generate_debate_content(topic, position, context)

        if len(content) < 20:
            return jsonify({'error': 'Generated content too short'}), 500

        logging.info(f"Generated {len(content)} characters")
        return jsonify({'content': content})

    except Exception as e:
        logging.error(f"Generation error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    # Test LM Studio connection
    lm_studio_ok = False
    try:
        response = requests.get("http://host.docker.internal:1234/v1/models", timeout=30)
        lm_studio_ok = response.status_code == 200
    except:
        pass

    return jsonify({
        'status': 'healthy',
        'service': 'text-generation',
        'lm_studio_connected': lm_studio_ok
    })


@app.route('/debug', methods=['POST'])
def debug():
    """Debug endpoint to test LM Studio directly"""
    try:
        data = request.get_json()
        topic = data.get('topic', 'test topic')

        # Make direct call to LM Studio
        payload = {
            "model": "openai-gpt-oss-20b-abliterated-uncensored-neo-imatrix",
            "messages": [{"role": "user", "content": f"Argue for: {topic}"}],
            "temperature": 0.7,
            "max_tokens": 100
        }

        response = requests.post(LM_STUDIO_URL, json=payload, timeout=6000)

        return jsonify({
            'status_code': response.status_code,
            'raw_response': response.json() if response.status_code == 200 else response.text,
            'url': LM_STUDIO_URL
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    logging.info("Starting text generation service...")
    app.run(host='0.0.0.0', port=8001, debug=False)
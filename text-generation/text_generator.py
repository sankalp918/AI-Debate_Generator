# Updated text-generation/text_generator.py
from flask import Flask, request, jsonify
import requests
import json
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Endpoint for LM Studio. If LM Studio is available this will be used to
# generate debate arguments. Otherwise the system falls back to static
# templates defined below. See generate_debate_content() for the logic.
LM_STUDIO_URL = "http://host.docker.internal:1234/v1/chat/completions"


def generate_debate_content(topic: str, position: str, previous_context: str = "") -> str:
    """Generate a debate argument for a given topic and position.

    The function will first attempt to use LM Studio to produce a high
    quality argument. If LM Studio is unavailable or returns an invalid
    response, the generator falls back to a set of handcrafted
    templates. When using the fallback, the previous context is used
    to cycle through the available templates so that repeated calls
    during multi‑round debates do not return the same text.

    Args:
        topic: The debate topic supplied by the user.
        position: Either "pro" (supporting) or "con" (opposing).
        previous_context: The accumulated conversation so far. This is a
            newline‑delimited string containing "Pro: ..." and
            "Con: ..." entries from earlier rounds.

    Returns:
        A string containing the generated argument.
    """

    # Try LM Studio first. This will produce more natural arguments and
    # allows the model to reference the previous context.
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

            # Handle different response structures returned by LM Studio.
            content = ""
            if 'choices' in result and len(result['choices']) > 0:
                choice = result['choices'][0]

                # Preferred: content inside the message field
                if 'message' in choice and 'content' in choice['message']:
                    content = choice['message']['content'].strip()
                # Some models return a reasoning field instead of content
                elif 'message' in choice and 'reasoning' in choice['message']:
                    reasoning = choice['message']['reasoning'].strip()
                    if reasoning and len(reasoning) > 20:
                        lines = reasoning.split('\n')
                        for line in lines:
                            if 'sentence' in line.lower() and len(line) > 50:
                                content = line.strip()
                                break
                # Fallback: direct text field on the choice
                elif 'text' in choice:
                    content = choice['text'].strip()

            # If the content is usable, return it
            if content and len(content) > 20 and content != "...":
                logging.info(f"LM Studio success: {len(content)} chars")
                return content
            else:
                logging.warning(f"LM Studio returned invalid content: '{content}'")
        else:
            logging.error(f"LM Studio API error: {response.status_code}")

    except Exception as e:
        logging.error(f"LM Studio error: {e}")

    # Fallback to template responses. Pass previous_context so the
    # template generator can select a different template for each
    # subsequent call.
    logging.info("Using fallback text generation")
    return generate_fallback_content(topic, position, previous_context)


def generate_fallback_content(topic: str, position: str, context: str = "") -> str:
    """Generate a deterministic fallback argument.

    When LM Studio is not available, fallback templates provide
    reasonable arguments for both sides of a topic. To avoid repeated
    audio across multiple rounds, this function uses the existing
    conversation context to rotate through the available templates.

    Args:
        topic: The debate topic.
        position: "pro" or "con", indicating which side is speaking.
        context: The conversation history accumulated so far, used to
            determine which template to select. It should contain lines
            beginning with "Pro:" and "Con:" for previously generated
            arguments.

    Returns:
        A string containing the selected fallback argument.
    """

    # Define template pools for each position. These are high quality
    # paragraphs intended to stand alone. See README for details.
    if position == 'pro':
        templates = [
            f"The transformation where {topic.lower()} represents an inevitable technological evolution that will ultimately benefit society. Historical evidence from the Industrial Revolution shows that while automation initially displaces workers, it creates new industries and higher‑skilled employment opportunities. Companies like Tesla and Amazon demonstrate how automation reduces costs while generating entirely new job categories in robotics, AI development, and human‑machine collaboration.",

            f"Economic data strongly supports that {topic.lower()} will drive unprecedented productivity gains. McKinsey research indicates that AI automation could contribute $13 trillion to global GDP by 2030 through increased efficiency and innovation. Countries embracing this transition, like Singapore and South Korea, are already seeing reduced workplace injuries, improved product quality, and new service sectors emerging around human creativity and emotional intelligence.",

            f"The technological capabilities now exist to make {topic.lower()} a reality within this timeframe. Recent advances in machine learning, robotics, and natural language processing have reached human‑level performance in manufacturing, customer service, and data analysis. Companies that resist this transition will become uncompetitive, while early adopters create safer, more fulfilling work environments focused on uniquely human skills."
        ]
    else:
        templates = [
            f"The premise that {topic.lower()} fundamentally misunderstands the complexity of human work and the limitations of current AI systems. While automation excels at repetitive tasks, most jobs require emotional intelligence, creative problem‑solving, and contextual judgment that remain beyond AI capabilities. The Oxford Economics study showing 20 million manufacturing jobs at risk fails to account for the 97 million new roles the World Economic Forum predicts AI will create.",

            f"Historical precedent suggests that {topic.lower()} overestimates the speed of technological adoption and underestimates human adaptability. The transition from agriculture to manufacturing took over a century, allowing gradual workforce adjustment. Current retraining programs and educational initiatives are already preparing workers for AI collaboration rather than replacement, as seen in Germany's Industry 4.0 initiative.",

            f"The assumption that {topic.lower()} ignores critical economic and social factors that will slow this transition. Regulatory frameworks, ethical concerns about algorithmic bias, and the high costs of AI implementation will create natural barriers. Additionally, consumer preferences often favor human interaction in healthcare, education, and hospitality sectors, ensuring sustained demand for human workers in these essential areas."
        ]

    # Default to hashing the topic if no context is provided. This keeps
    # single round debates deterministic.
    template_index = hash(topic) % len(templates)

    # If context is supplied, count the number of prior statements for
    # this position and use it to rotate through templates. Each time
    # the same side speaks, the index increments, ensuring that
    # successive calls select different templates. When the number of
    # rounds exceeds the number of templates, the index wraps around.
    if context:
        try:
            # Split context into non‑empty lines
            lines = [line.strip() for line in context.split('\n') if line.strip()]
            # Count how many times this position has already spoken
            if position == 'pro':
                count = sum(1 for line in lines if line.lower().startswith('pro:'))
            else:
                count = sum(1 for line in lines if line.lower().startswith('con:'))
            template_index = count % len(templates)
        except Exception as e:
            # Log and fall back to hashed topic index on any failure
            logging.warning(f"Context parsing error in fallback: {e}")

    return templates[template_index]


@app.route('/generate', methods=['POST'])
def generate():
    """HTTP endpoint for debate content generation.

    Expects a JSON payload with the following fields:

      • topic: the debate topic (required)
      • position: 'pro' or 'con' (optional, defaults to 'pro')
      • context: the conversation context so far (optional)

    Returns a JSON object containing the generated content or an error message.
    """
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
    """Health check endpoint.

    Returns the service status and indicates whether LM Studio is
    reachable. Useful for orchestrator service to verify the text
    generation component is online.
    """
    lm_studio_ok = False
    try:
        response = requests.get("http://host.docker.internal:1234/v1/models", timeout=50)
        lm_studio_ok = response.status_code == 200
    except Exception:
        pass

    return jsonify({
        'status': 'healthy',
        'service': 'text-generation',
        'lm_studio_connected': lm_studio_ok
    })


@app.route('/debug', methods=['POST'])
def debug():
    """Debug endpoint to call LM Studio directly.

    This helper allows you to test the connection to LM Studio outside
    the normal debate generation flow. It accepts a topic in the POST
    body and returns the raw response from LM Studio.
    """
    try:
        data = request.get_json()
        topic = data.get('topic', 'test topic')

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
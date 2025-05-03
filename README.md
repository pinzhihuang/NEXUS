# LIVE WEEKLY BOT

A Python-based bot that generates weekly news summaries for Chinese international students at NYU using the Perplexity AI API.

## Features

- Generates 5 relevant news summaries daily
- Focuses on topics relevant to Chinese international students
- Sources news from the past 7 days
- Includes verified sources for each summary
- Maintains neutral and professional tone

## Requirements

- Python 3.x
- Perplexity AI API key
- Required Python packages (see requirements.txt)

## Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create a `.env` file and add your Perplexity AI API key:
   ```
   PPLX_API_KEY=your_api_key_here
   ```

## Usage

Run the main script:
```bash
python Main.py
```

The script will generate news summaries and save them in markdown format.

## License

MIT License 
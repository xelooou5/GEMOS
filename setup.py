from setuptools import setup, find_packages

setup(
    name="gemos",
    version="1.0.0",
    author="xelooou5",
    description="GEM OS - AI-Coordinated Voice Assistant",
    long_description="Voice assistant coordinated by Amazon Q, Claude, and Gemini",
    url="https://github.com/xelooou5/GEMOS",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "pyttsx3>=2.90",
        "speechrecognition>=3.10.0",
        "pyaudio>=0.2.11",
        "faster-whisper>=0.10.0",
        "boto3>=1.34.0",
        "python-dotenv>=1.0.0",
        "numpy>=1.24.3",
        "requests>=2.31.0",
        "sounddevice>=0.4.6",
        "google-cloud-speech>=2.21.0",
        "google-generativeai>=0.3.0",
        "anthropic>=0.7.0",
    ],
)

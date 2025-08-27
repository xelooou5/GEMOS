from setuptools import setup, find_packages

setup(
    name="gemos",
    version="1.0.0",
    author="xelooou5",
    description="GEM OS - Generative Enhanced Microphone Operating System",
    long_description="AI-powered voice assistant with accessibility features",
    url="https://github.com/xelooou5/GEMOS",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pyttsx3==2.90",
        "speechrecognition==3.10.0",
        "pyaudio==0.2.11",
        "faster-whisper==0.10.0",
        "boto3==1.34.0",
        "python-dotenv==1.0.0",
        "numpy==1.24.3",
        "requests==2.31.0",
        "asyncio-mqtt==0.16.1",
        "aiofiles==23.2.1",
    ],
)

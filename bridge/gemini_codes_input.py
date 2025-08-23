#!/usr/bin/env python3
"""
Gemini Codes Input - Capture and integrate Gemini's 6 codes
"""

import sys
from enhanced_ai_bridge import EnhancedAIBridge

def capture_gemini_codes():
    """Capture the 6 codes from Gemini"""
    bridge = EnhancedAIBridge()
    
    print("🤖 Gemini Code Integration System")
    print("=" * 50)
    print("Please paste Gemini's 6 codes below:")
    print("(Press Ctrl+D when finished)")
    print("-" * 30)
    
    try:
        codes = sys.stdin.read().strip()
        if codes:
            # Log to AI bridge
            bridge.send_message(
                sender='gemini',
                message=f"6 Codes for GEM OS Integration:\n\n{codes}",
                recipients=['amazon_q', 'copilot']
            )
            
            print("\n✅ Gemini's 6 codes captured and logged!")
            print("📁 Saved to AI bridge for integration")
            
            # Save to separate file for processing
            with open('/home/oem/gemini_6_codes.txt', 'w') as f:
                f.write(codes)
            
            return codes
        else:
            print("No codes provided.")
            return None
            
    except KeyboardInterrupt:
        print("\nCancelled.")
        return None

if __name__ == "__main__":
    codes = capture_gemini_codes()
    if codes:
        print(f"\n📊 Captured {len(codes.split('```'))-1} code blocks")
        print("Ready for Amazon Q to analyze and integrate!")
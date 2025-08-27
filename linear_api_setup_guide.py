#!/usr/bin/env python3
"""
🔥 LINEAR API SETUP GUIDE FOR GEM OS
Step-by-step guide to create API key for Linear integration
"""

import asyncio

class LinearAPISetupGuide:
    """Guide for setting up Linear API for GEM OS"""
    
    def __init__(self):
        self.workspace_url = "https://linear.app/gemos"
        self.api_settings_url = "https://linear.app/gemos/settings/api"
        
    async def show_api_setup_guide(self):
        """Show complete API setup guide"""
        print("🔥" + "=" * 70)
        print("🔥 LINEAR API SETUP GUIDE FOR GEM OS")
        print("🔥 STEP-BY-STEP INSTRUCTIONS")
        print("🔥" + "=" * 70)
        
        await self.step_1_access_api_settings()
        await self.step_2_create_personal_api_key()
        await self.step_3_configure_oauth_application()
        await self.step_4_setup_environment()
        await self.step_5_test_integration()
        
    async def step_1_access_api_settings(self):
        """Step 1: Access API settings"""
        print("\n📋 STEP 1: ACCESS API SETTINGS")
        print("=" * 40)
        
        print(f"🔗 Go to: {self.api_settings_url}")
        print("\n📍 Navigation path:")
        print("   1. Open Linear workspace: https://linear.app/gemos")
        print("   2. Click Settings (gear icon)")
        print("   3. In sidebar, click 'API' under Administration")
        print("   4. You should see API settings page")
        
        print("\n✅ What you should see:")
        print("   • API settings page with tabs")
        print("   • 'Personal API keys' tab")
        print("   • 'Applications' tab")
        print("   • Option to create new API key")
        
    async def step_2_create_personal_api_key(self):
        """Step 2: Create personal API key"""
        print("\n🔑 STEP 2: CREATE PERSONAL API KEY")
        print("=" * 40)
        
        print("📋 Instructions:")
        print("   1. Click 'Personal API keys' tab")
        print("   2. Click 'Create new key' or '+' button")
        print("   3. Enter key details:")
        print("      • Name: 'GEM OS Development'")
        print("      • Description: 'API key for GEM OS AI team integration'")
        print("      • Scopes: Select 'read' and 'write'")
        print("   4. Click 'Create key'")
        print("   5. COPY THE KEY IMMEDIATELY (shown only once)")
        
        print("\n⚠️ IMPORTANT:")
        print("   • API key is shown only once - copy it now!")
        print("   • Store securely - don't share publicly")
        print("   • Key format: lin_api_xxxxxxxxxxxxxxxxx")
        
    async def step_3_configure_oauth_application(self):
        """Step 3: Configure OAuth application for AI agents"""
        print("\n🤖 STEP 3: CONFIGURE OAUTH APPLICATION (FOR AI AGENTS)")
        print("=" * 50)
        
        print("📋 Instructions:")
        print("   1. Click 'Applications' tab")
        print("   2. Click 'Create new application'")
        print("   3. Fill in application details:")
        print("      • Application name: 'GEM OS AI Team'")
        print("      • Developer name: 'GEM OS Development Team'")
        print("      • Developer URL: 'https://github.com/your-username/gem'")
        print("      • Description: 'AI agents for GEM OS accessibility project'")
        print("      • Callback URLs: 'http://localhost:8080/callback'")
        print("      • GitHub username: (optional)")
        print("   4. Enable 'Refresh tokens' (recommended)")
        print("   5. Click 'Create'")
        
        print("\n🎯 OAuth URL with actor=app:")
        print("   https://linear.app/oauth/authorize?")
        print("   client_id=YOUR_CLIENT_ID&")
        print("   redirect_uri=http://localhost:8080/callback&")
        print("   response_type=code&")
        print("   scope=read,write&")
        print("   actor=app")
        
    async def step_4_setup_environment(self):
        """Step 4: Setup environment configuration"""
        print("\n⚙️ STEP 4: SETUP ENVIRONMENT CONFIGURATION")
        print("=" * 45)
        
        print("📝 Add to .env file:")
        print("   # Linear API Configuration")
        print("   LINEAR_API_KEY=lin_api_your_key_here")
        print("   LINEAR_WORKSPACE=gemos")
        print("   LINEAR_TEAM_KEY=GEM")
        print("   ")
        print("   # OAuth Application (for AI agents)")
        print("   LINEAR_CLIENT_ID=your_client_id_here")
        print("   LINEAR_CLIENT_SECRET=your_client_secret_here")
        print("   LINEAR_REDIRECT_URI=http://localhost:8080/callback")
        
        print("\n🔧 Configuration example:")
        env_example = '''
# .env file example
LINEAR_API_KEY=lin_api_abc123def456ghi789
LINEAR_WORKSPACE=gemos
LINEAR_TEAM_KEY=GEM
LINEAR_CLIENT_ID=oauth_client_123
LINEAR_CLIENT_SECRET=oauth_secret_456
LINEAR_REDIRECT_URI=http://localhost:8080/callback
'''
        print(env_example)
        
    async def step_5_test_integration(self):
        """Step 5: Test Linear integration"""
        print("\n🧪 STEP 5: TEST LINEAR INTEGRATION")
        print("=" * 40)
        
        print("📋 Testing steps:")
        print("   1. Save API key to .env file")
        print("   2. Run: python3 test_linear_integration.py")
        print("   3. Verify connection to Linear API")
        print("   4. Test creating issues in GEM team")
        print("   5. Verify AI agents can post updates")
        
        print("\n✅ Success indicators:")
        print("   • API connection successful")
        print("   • GEM team found and accessible")
        print("   • Issues can be created")
        print("   • AI agents can post as themselves")
        
        print("\n❌ Troubleshooting:")
        print("   • Check API key is correct")
        print("   • Verify workspace name (gemos)")
        print("   • Ensure team key is correct (GEM)")
        print("   • Check network connectivity")
        
    async def show_next_steps(self):
        """Show next steps after API setup"""
        print("\n🚀 NEXT STEPS AFTER API SETUP:")
        print("=" * 40)
        
        print("🎯 Immediate actions:")
        print("   1. Create Linear API key")
        print("   2. Add to .env file")
        print("   3. Test connection")
        print("   4. Create initial GEM OS issues")
        print("   5. Start tracking AI team progress")
        
        print("\n📊 What Linear will track:")
        print("   • Sprint progress and milestones")
        print("   • Bug reports and fixes")
        print("   • Feature development")
        print("   • Accessibility testing results")
        print("   • AI agent coordination")
        print("   • Release preparation")
        
        print("\n🤖 AI Agent Integration:")
        print("   • Each AI agent posts their own updates")
        print("   • Automatic issue creation for tasks")
        print("   • Progress tracking for 20-day mission")
        print("   • Professional project management")

async def main():
    """Run Linear API setup guide"""
    print("🔥 LINEAR API SETUP GUIDE FOR GEM OS")
    print("🎯 Professional project management for accessibility mission")
    print("=" * 70)
    
    guide = LinearAPISetupGuide()
    
    await guide.show_api_setup_guide()
    await guide.show_next_steps()
    
    print("\n🔥" + "=" * 70)
    print("🔥 LINEAR API SETUP GUIDE COMPLETE")
    print("🔥 FOLLOW STEPS TO ENABLE PROFESSIONAL PROJECT TRACKING")
    print("🔥 GEM OS AI TEAM READY FOR LINEAR INTEGRATION!")
    print("🔥" + "=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
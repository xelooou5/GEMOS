#!/usr/bin/env python3
"""
🔥 CURSOR LINEAR OAUTH INTEGRATION - GEM OS PROJECT
Handle Cursor Linear OAuth authorization
"""

import webbrowser
import urllib.parse

class CursorLinearOAuth:
    """Handle Cursor Linear OAuth integration"""
    
    def __init__(self):
        self.oauth_url = "https://linear.app/oauth/authorize?client_id=93cf1a5736ba981f1fb61c4cb24f518d&response_type=code&state=eyJ1c2VySWQiOjI4NzUwMjU0MiwidGltZXN0YW1wIjoxNzU2MzE5MzkyMzUyLCJyYW5kb20iOiJlZDYwYzIzMGI1ODI3NDU4ZDk1ZWQ5NDhiODFkZGZkNzNkN2I4Y2QwZDlkYmI0MjIxZDAyYTcxOWZiMWU5Y2ZiIn0%3D&prompt=consent&redirect_uri=https%3A%2F%2Fapi2.cursor.sh%2Flinear%2Fcallback&actor=app&scope=read%2Cwrite%2Cissues%3Acreate%2Ccomments%3Acreate%2Capp%3Aassignable%2Capp%3Amentionable"
        
    def parse_oauth_params(self):
        """Parse OAuth URL parameters"""
        parsed = urllib.parse.urlparse(self.oauth_url)
        params = urllib.parse.parse_qs(parsed.query)
        
        print("🔑 CURSOR LINEAR OAUTH PARAMETERS:")
        print(f"   Client ID: {params.get('client_id', [''])[0]}")
        print(f"   Response Type: {params.get('response_type', [''])[0]}")
        print(f"   Redirect URI: {urllib.parse.unquote(params.get('redirect_uri', [''])[0])}")
        print(f"   Scopes: {params.get('scope', [''])[0]}")
        
    def authorize_cursor_linear(self):
        """Authorize Cursor with Linear"""
        print("🔥 CURSOR LINEAR OAUTH AUTHORIZATION")
        print("=" * 50)
        
        print("🎯 AUTHORIZATION STEPS:")
        print("1. Opening Linear OAuth authorization...")
        print("2. Grant permissions to Cursor")
        print("3. Cursor will be authorized for Linear integration")
        
        # Open OAuth URL
        webbrowser.open(self.oauth_url)
        
        print("\n✅ OAuth URL opened in browser")
        print("🔑 Grant permissions to complete integration")
        
    def show_granted_permissions(self):
        """Show permissions being granted"""
        print("\n🔐 PERMISSIONS BEING GRANTED TO CURSOR:")
        print("   ✅ read - Read Linear data")
        print("   ✅ write - Write Linear data") 
        print("   ✅ issues:create - Create issues")
        print("   ✅ comments:create - Create comments")
        print("   ✅ app:assignable - Assign issues to Cursor")
        print("   ✅ app:mentionable - Mention Cursor in Linear")

def main():
    """Main OAuth handler"""
    oauth = CursorLinearOAuth()
    oauth.parse_oauth_params()
    oauth.show_granted_permissions()
    oauth.authorize_cursor_linear()
    
    print("\n🔥 CURSOR LINEAR OAUTH INTEGRATION READY!")
    print("📋 Cursor can now manage Linear issues automatically")
    print("🤖 AI team coordination through Cursor + Linear")

if __name__ == "__main__":
    main()
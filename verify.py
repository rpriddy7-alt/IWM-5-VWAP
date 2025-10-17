#!/usr/bin/env python3
"""
System verification script - checks that all components are properly configured.
Run this before deployment to catch issues early.
"""
import sys
import importlib
from pathlib import Path

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print('='*60)

def print_check(name, passed, details=""):
    status = "✓" if passed else "✗"
    color = "\033[92m" if passed else "\033[91m"
    reset = "\033[0m"
    print(f"{color}{status}{reset} {name}")
    if details:
        print(f"  → {details}")

def main():
    print_header("IWM Momentum System - Pre-Flight Check")
    
    all_passed = True
    
    # 1. Check Python version
    print_header("Python Environment")
    import sys
    py_version = sys.version_info
    version_ok = py_version >= (3, 9)
    print_check(
        "Python version",
        version_ok,
        f"{py_version.major}.{py_version.minor}.{py_version.micro}"
    )
    all_passed = all_passed and version_ok
    
    # 2. Check dependencies
    print_header("Dependencies")
    required_modules = [
        'websocket',
        'requests',
        'numpy',
        'pytz',
        'dotenv'
    ]
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            print_check(f"{module}", True)
        except ImportError:
            print_check(f"{module}", False, "Not installed")
            all_passed = False
    
    # 3. Check configuration
    print_header("Configuration")
    try:
        from config import Config
        validation = Config.validate()
        
        print_check(
            "Config module",
            True,
            "Loaded successfully"
        )
        
        for error in validation['errors']:
            print_check(error, False)
            all_passed = False
        
        if validation['valid']:
            print_check("All required API keys", True)
            print(f"\n{Config.get_config_summary()}")
        
    except Exception as e:
        print_check("Config module", False, str(e))
        all_passed = False
    
    # 4. Check core modules
    print_header("Core Modules")
    core_modules = [
        ('polygon_client', 'Polygon API client'),
        ('contract_selector', 'Contract selector'),
        ('signals', 'Signal detection'),
        ('risk_manager', 'Risk manager'),
        ('alerts', 'Alert system'),
        ('logger', 'Logging'),
        ('utils', 'Utilities')
    ]
    
    for module_name, description in core_modules:
        try:
            importlib.import_module(module_name)
            print_check(description, True, f"{module_name}.py")
        except Exception as e:
            print_check(description, False, f"Import error: {e}")
            all_passed = False
    
    # 5. Check file structure
    print_header("File Structure")
    required_files = [
        'main.py',
        'config.py',
        'requirements.txt',
        'README.md',
        'render.yaml'
    ]
    
    for filename in required_files:
        exists = Path(filename).exists()
        print_check(filename, exists)
        all_passed = all_passed and exists
    
    # 6. Check .env setup
    print_header("Environment Setup")
    env_exists = Path('.env').exists()
    example_exists = Path('.env.example').exists()
    
    print_check(".env.example", example_exists)
    print_check(".env (local)", env_exists, 
               "Found" if env_exists else "Create from .env.example")
    
    # 7. Test instantiation (without connecting)
    print_header("Component Initialization Test")
    try:
        from polygon_client import PolygonWebSocketClient, PolygonRESTClient
        from contract_selector import ContractSelector
        from signals import MomentumSignal, SimpleExitMonitor
        from risk_manager import RiskManager
        from alerts import PushoverClient
        
        # Try instantiating each component
        components = [
            ('WebSocket Client (stocks)', lambda: PolygonWebSocketClient('stocks')),
            ('WebSocket Client (options)', lambda: PolygonWebSocketClient('options')),
            ('REST Client', lambda: PolygonRESTClient()),
            ('Contract Selector', lambda: ContractSelector()),
            ('Momentum Signal', lambda: MomentumSignal()),
            ('Exit Monitor', lambda: SimpleExitMonitor()),
            ('Risk Manager', lambda: RiskManager()),
            ('Pushover Client', lambda: PushoverClient())
        ]
        
        for name, factory in components:
            try:
                obj = factory()
                print_check(name, True, "Instantiated successfully")
            except Exception as e:
                print_check(name, False, f"Error: {e}")
                all_passed = False
                
    except Exception as e:
        print_check("Component initialization", False, str(e))
        all_passed = False
    
    # 8. Summary
    print_header("Summary")
    if all_passed:
        print("\n🎉 \033[92mALL CHECKS PASSED\033[0m")
        print("\nYou're ready to deploy!")
        print("\nNext steps:")
        print("  1. Test locally: python main.py")
        print("  2. Commit changes: git add . && git commit -m 'Ready for deploy'")
        print("  3. Push to GitHub: git push origin IWM-MAIN")
        print("  4. Deploy to Render (auto-deploys if connected)")
        return 0
    else:
        print("\n❌ \033[91mSOME CHECKS FAILED\033[0m")
        print("\nPlease fix the issues above before deploying.")
        print("\nCommon fixes:")
        print("  - Missing dependencies: pip install -r requirements.txt")
        print("  - Missing .env: cp .env.example .env && edit .env")
        print("  - Invalid API keys: check .env credentials")
        return 1

if __name__ == "__main__":
    sys.exit(main())



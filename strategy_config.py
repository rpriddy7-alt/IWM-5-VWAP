"""
Strategy Configuration for Miyagi Multi-Strategy System
Allows easy configuration and toggling of different strategies.
"""
import os
from typing import Dict, Any
from logger import setup_logger

logger = setup_logger("StrategyConfig")


class StrategyConfig:
    """Configuration for Miyagi multi-strategy system."""
    
    # Strategy toggles (can be controlled via environment variables)
    ENABLE_VWAP_STRATEGY: bool = os.getenv('ENABLE_VWAP_STRATEGY', 'true').lower() in ['true', '1', 'yes']
    ENABLE_OVERNIGHT_BIAS_STRATEGY: bool = os.getenv('ENABLE_OVERNIGHT_BIAS_STRATEGY', 'true').lower() in ['true', '1', 'yes']
    
    # Strategy priorities (higher number = higher priority)
    STRATEGY_PRIORITIES = {
        'vwap': 1,
        'overnight_bias': 2  # Higher priority for new strategy
    }
    
    # Position limits per strategy
    MAX_POSITIONS_PER_STRATEGY = {
        'vwap': 1,
        'overnight_bias': 1
    }
    
    # Total position limits
    MAX_TOTAL_POSITIONS: int = int(os.getenv('MAX_TOTAL_POSITIONS', '2'))
    MAX_DAILY_LOSS: float = float(os.getenv('MAX_DAILY_LOSS', '700.0'))
    
    # Strategy-specific settings
    VWAP_STRATEGY_SETTINGS = {
        'entry_windows': {
            'primary': {'start': '09:45', 'end': '11:00'},
            'secondary': {'start': '13:30', 'end': '14:15'}
        },
        'cooldown_minutes': 5,
        'max_retests': 2
    }
    
    OVERNIGHT_BIAS_STRATEGY_SETTINGS = {
        'entry_windows': {
            'primary': {'start': '09:45', 'end': '11:00'},
            'secondary': {'start': '13:30', 'end': '14:15'}
        },
        'position_sizing': {
            'initial': 0.33,  # 1/3 of capital
            'add': 0.33,      # 1/3 for retest
            'reserve': 0.34   # 1/3 reserve
        },
        'risk_per_trade_pct': 3.0,  # 3% max risk per trade
        'time_stop_minutes': 45,
        'profit_scales': {
            'scale_1': {'pct': 30, 'scale_out': 0.25},
            'scale_2': {'pct': 70, 'scale_out': 0.5}
        }
    }
    
    @classmethod
    def get_active_strategies(cls) -> Dict[str, bool]:
        """Get dictionary of active strategies."""
        return {
            'vwap': cls.ENABLE_VWAP_STRATEGY,
            'overnight_bias': cls.ENABLE_OVERNIGHT_BIAS_STRATEGY
        }
    
    @classmethod
    def get_strategy_priority(cls, strategy_name: str) -> int:
        """Get priority for a strategy."""
        return cls.STRATEGY_PRIORITIES.get(strategy_name, 0)
    
    @classmethod
    def get_max_positions_for_strategy(cls, strategy_name: str) -> int:
        """Get max positions for a specific strategy."""
        return cls.MAX_POSITIONS_PER_STRATEGY.get(strategy_name, 1)
    
    @classmethod
    def can_add_position(cls, strategy_name: str, current_positions: Dict) -> bool:
        """Check if we can add a new position for a strategy."""
        # Check total position limit
        if len(current_positions) >= cls.MAX_TOTAL_POSITIONS:
            return False
        
        # Check strategy-specific limit
        strategy_positions = len([
            p for p in current_positions.values() 
            if p.get('strategy') == strategy_name
        ])
        
        if strategy_positions >= cls.get_max_positions_for_strategy(strategy_name):
            return False
        
        return True
    
    @classmethod
    def get_strategy_settings(cls, strategy_name: str) -> Dict[str, Any]:
        """Get settings for a specific strategy."""
        if strategy_name == 'vwap':
            return cls.VWAP_STRATEGY_SETTINGS
        elif strategy_name == 'overnight_bias':
            return cls.OVERNIGHT_BIAS_STRATEGY_SETTINGS
        else:
            return {}
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate strategy configuration."""
        errors = []
        warnings = []
        
        # Check if at least one strategy is enabled
        active_strategies = cls.get_active_strategies()
        if not any(active_strategies.values()):
            errors.append("At least one strategy must be enabled")
        
        # Check position limits
        if cls.MAX_TOTAL_POSITIONS < 1:
            errors.append("MAX_TOTAL_POSITIONS must be at least 1")
        
        if cls.MAX_DAILY_LOSS > 0:
            warnings.append("MAX_DAILY_LOSS is positive - this should be negative")
        
        # Check strategy priorities
        priorities = list(cls.STRATEGY_PRIORITIES.values())
        if len(priorities) != len(set(priorities)):
            warnings.append("Strategy priorities should be unique")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'active_strategies': active_strategies
        }
    
    @classmethod
    def get_config_summary(cls) -> str:
        """Get configuration summary."""
        validation = cls.validate_config()
        active_strategies = cls.get_active_strategies()
        
        summary = f"""
Miyagi Multi-Strategy Configuration:
  Active Strategies: {', '.join([k for k, v in active_strategies.items() if v])}
  Max Total Positions: {cls.MAX_TOTAL_POSITIONS}
  Max Daily Loss: ${cls.MAX_DAILY_LOSS}
  
Strategy Settings:
"""
        
        for strategy, enabled in active_strategies.items():
            if enabled:
                settings = cls.get_strategy_settings(strategy)
                summary += f"  {strategy.upper()}:\n"
                summary += f"    Entry Windows: {settings.get('entry_windows', {})}\n"
                if 'position_sizing' in settings:
                    summary += f"    Position Sizing: {settings['position_sizing']}\n"
                if 'cooldown_minutes' in settings:
                    summary += f"    Cooldown: {settings['cooldown_minutes']} minutes\n"
        
        if validation['warnings']:
            summary += "\nWarnings:\n"
            for warning in validation['warnings']:
                summary += f"  - {warning}\n"
        
        return summary


if __name__ == "__main__":
    # Quick config check
    validation = StrategyConfig.validate_config()
    if validation['valid']:
        print("✓ Strategy configuration valid")
        print(StrategyConfig.get_config_summary())
    else:
        print("✗ Strategy configuration errors:")
        for error in validation['errors']:
            print(f"  - {error}")

export interface OptionPosition {
  id: string
  underlying_symbol: string
  option_symbol: string
  strike: number
  expiration_date: string
  dte_at_entry: number
  contracts: number
  premium_received: number
  total_credit: number
  current_price: number | null
  unrealized_pnl: number | null
  status: 'OPEN' | 'CLOSING' | 'CLOSED' | 'EXPIRED' | 'ASSIGNED'
  opened_at: string
  closed_at: string | null
  rule_id: string | null
}

export interface SellPutRule {
  id: string
  name: string
  enabled: boolean
  symbols: Array<{ symbol: string; priority: number }>
  min_dte: number
  max_dte: number
  min_premium_mode: 'pct' | 'dollar'
  min_premium_pct: number
  min_premium_dollar: number | null
  max_premium_pct: number | null
  min_daily_drop_pct: number | null
  max_daily_drop_pct: number | null
  profit_target_pct: number
  profit_approach_pct: number | null
  stop_loss_pct: number | null
  max_open_positions: number
  position_size_mode: 'pct' | 'contracts'
  position_size_pct: number
  position_size_contracts: number | null
  scan_interval_minutes: number
  strategy_type: 'SELL_PUT' | 'SELL_COVERED_CALL'
  min_strike_otm_pct: number | null
  itm_action: 'let_assign' | 'roll'
  roll_when_dte: number
  roll_target_weeks: number
  strike_min: number | null
  strike_max: number | null
  max_premium_dollar: number | null
  bid_ask_fill_pct: number
  min_iv_pct: number | null
  max_iv_pct: number | null
  last_error: string | null
  last_error_at: string | null
  last_scan_note: string | null
  last_scanned_at: string | null
}

export interface DailySnapshot {
  snapshot_date: string
  total_portfolio_value: number | null
  buying_power: number | null
  open_positions_count: number
  total_unrealized_pnl: number
  daily_realized_pnl: number
  cumulative_realized_pnl: number
}

export interface PerformanceSummary {
  period: string
  realized_pnl: number
  unrealized_pnl: number
  total_pnl: number
  pnl_pct: number | null
  trades_closed: number
  win_rate: number | null
  portfolio_value: number | null
}

export interface Order {
  id: string
  schwab_order_id: string | null
  order_type: string
  status: string
  symbol: string
  quantity: number
  limit_price: number
  fill_price: number | null
  is_gtc: boolean
  created_at: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface AccountHolding {
  symbol: string
  description: string
  asset_type: 'EQUITY' | 'OPTION'
  quantity: number
  market_value: number | null
  day_change_pct: number | null
  // Option-specific
  strike?: number
  expiration_date?: string
  put_call?: 'PUT' | 'CALL'
  average_price?: number | null
  dte?: number | null
}

export interface AccountData {
  portfolio_value: number | null
  buying_power: number | null
  cash_balance: number | null
  holdings: AccountHolding[]
}

export interface StrategyListResponse {
  strategies: string[];
  defaultSymbols: string[];
}

export interface BacktestSummary {
  symbol: string;
  totalTrades: number;
  netPnl: number;
  returnPct: number;
  winRate: number;
}

export interface TradeRecord {
  timestamp?: string;
  symbol: string;
  action?: string;
  quantity?: number;
  price?: number;
  cash_after?: number;
  market_value_after?: number;
  equity_after?: number;
  reason?: string;
  trade_type?: string;
  position_after?: number;
  direction?: string;
  entry_price?: number;
  exit_price?: number;
  entry_time?: string;
  exit_time?: string;
  pnl?: number;
}

export interface EquityPoint {
  datetime: string;
  cash: number;
  market_value: number;
  equity: number;
  baseline_equity?: number;
  [key: string]: string | number | undefined;
}

export interface BacktestResponse {
  start: string;
  end: string;
  initialCapital: number;
  endingEquity: number;
  netProfit: number;
  returnPct: number;
  annualizedReturn: number;
  maxDrawdown: number;
  trades: TradeRecord[];
  closedTrades: TradeRecord[];
  equityCurve: EquityPoint[];
  summaries: BacktestSummary[];
  cacheFiles?: string[];
}

export interface BacktestFormValues {
  strategy: string;
  symbols: string[];
  timeframe: string;
  start?: string;
  end?: string;
  initialCapital?: number;
  commission?: number;
  writeCache: boolean;
}

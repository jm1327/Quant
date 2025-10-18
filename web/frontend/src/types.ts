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

export type OrderSide = "BUY" | "SELL";

export type SimulatedOrderType = "MARKET" | "LIMIT" | "STOP";

export interface SimulatedOrder {
  id: number;
  symbol: string;
  side: OrderSide;
  quantity: number;
  orderType: SimulatedOrderType;
  status: "SUBMITTED" | "WORKING" | "FILLED" | "CANCELLED";
  limitPrice: number | null;
  fillPrice: number | null;
  createdAt: string;
  filledAt: string | null;
  notes: string;
}

export interface CreateSimulatedOrderPayload {
  symbol: string;
  side: OrderSide;
  quantity: number;
  price: number;
  orderType: SimulatedOrderType;
  notes?: string;
}

export interface PortfolioCashAmount {
  currency: string;
  value: number | null;
  raw: string | number | null;
  accountName?: string;
}

export interface PortfolioCashBalance {
  label: string;
  amounts: PortfolioCashAmount[];
}

export interface PortfolioPosition {
  symbol?: string;
  position: number;
  avgCost: number | null;
  currency?: string;
  exchange?: string;
  secType?: string;
  marketPrice?: number | null;
  marketValue?: number | null;
  dailyPnl?: number | null;
  unrealizedPnl?: number | null;
  unrealizedPnlRatio?: number | null;
  realizedPnl?: number | null;
}

export interface PortfolioHolding {
  symbol?: string;
  position: number;
  marketValue: number | null;
  unrealizedPnl: number | null;
  realizedPnl: number | null;
  averageCost: number | null;
  currency?: string;
  accountName?: string;
}

export interface PortfolioCurrencyTotal {
  currency: string;
  marketValue: number;
}

export interface PortfolioSnapshot {
  retrievedAt: string;
  cashBalances: PortfolioCashBalance[];
  positions: PortfolioPosition[];
  holdings: PortfolioHolding[];
  marketValueByCurrency: PortfolioCurrencyTotal[];
}

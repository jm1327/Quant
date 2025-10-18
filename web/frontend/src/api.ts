import axios from "axios";
import type {
  BacktestFormValues,
  BacktestResponse,
  CreateSimulatedOrderPayload,
  PortfolioSnapshot,
  SimulatedOrder,
  StrategyListResponse,
} from "./types";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

export async function fetchStrategies(): Promise<StrategyListResponse> {
  const response = await api.get<StrategyListResponse>("/api/strategies/");
  return response.data;
}

export interface RunBacktestOptions {
  dataDir?: string;
  cacheDir?: string;
}

export async function runBacktest(
  values: BacktestFormValues,
  options: RunBacktestOptions = {}
): Promise<BacktestResponse> {
  const payload: Record<string, unknown> = {
    strategy: values.strategy,
    symbols: values.symbols,
    timeframe: values.timeframe,
    write_cache: values.writeCache,
  };

  if (values.start) {
    payload.start = values.start;
  }
  if (values.end) {
    payload.end = values.end;
  }
  if (values.initialCapital !== undefined) {
    payload.initial_capital = values.initialCapital;
  }
  if (values.commission !== undefined) {
    payload.commission = values.commission;
  }
  if (options.dataDir) {
    payload.data_dir = options.dataDir;
  }
  if (options.cacheDir) {
    payload.cache_dir = options.cacheDir;
  }

  const response = await api.post<BacktestResponse>("/api/backtests/", payload);
  return response.data;
}

export async function fetchSimulatedOrders(): Promise<SimulatedOrder[]> {
  const response = await api.get<SimulatedOrder[]>("/api/simulated-orders/");
  return response.data;
}

export async function createSimulatedOrder(payload: CreateSimulatedOrderPayload): Promise<SimulatedOrder> {
  const response = await api.post<SimulatedOrder>("/api/simulated-orders/", payload);
  return response.data;
}

export async function fetchPortfolioSnapshot(): Promise<PortfolioSnapshot> {
  const response = await api.get<PortfolioSnapshot>("/api/portfolio/");
  return response.data;
}

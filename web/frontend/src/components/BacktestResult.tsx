import { Card, Col, Divider, Empty, List, Row, Space, Statistic, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import type { BacktestResponse, BacktestSummary, TradeRecord } from "../types";
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface BacktestResultProps {
  result?: BacktestResponse;
  loading: boolean;
  error?: string;
}

const formatCurrency = (value: number) => `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const formatPercent = (value: number) => `${(value * 100).toFixed(2)}%`;

const summaryColumns: ColumnsType<BacktestSummary> = [
  { title: "Symbol", dataIndex: "symbol", key: "symbol" },
  { title: "Trades", dataIndex: "totalTrades", key: "totalTrades" },
  {
    title: "Net PnL",
    dataIndex: "netPnl",
    key: "netPnl",
    render: (value: number) => formatCurrency(value),
  },
  {
    title: "Return",
    dataIndex: "returnPct",
    key: "returnPct",
    render: (value: number) => formatPercent(value),
  },
  {
    title: "Win Rate",
    dataIndex: "winRate",
    key: "winRate",
    render: (value: number) => formatPercent(value),
  },
];

const tradesColumns: ColumnsType<TradeRecord> = [
  { title: "Time", dataIndex: "timestamp", key: "timestamp" },
  { title: "Symbol", dataIndex: "symbol", key: "symbol" },
  { title: "Action", dataIndex: "action", key: "action" },
  { title: "Quantity", dataIndex: "quantity", key: "quantity" },
  {
    title: "Price",
    dataIndex: "price",
    key: "price",
    render: (value?: number) => (typeof value === "number" ? formatCurrency(value) : "-"),
  },
  {
    title: "Reason",
    dataIndex: "reason",
    key: "reason",
    render: (value?: string) => (value ? <Tag>{value}</Tag> : null),
  },
  {
    title: "Equity",
    dataIndex: "equity_after",
    key: "equity_after",
    render: (value?: number) => (typeof value === "number" ? formatCurrency(value) : "-"),
  },
];

const closedTradesColumns: ColumnsType<TradeRecord> = [
  { title: "Symbol", dataIndex: "symbol", key: "symbol" },
  { title: "Direction", dataIndex: "direction", key: "direction" },
  { title: "Quantity", dataIndex: "quantity", key: "quantity" },
  {
    title: "Entry",
    dataIndex: "entry_price",
    key: "entry_price",
    render: (value?: number) => (typeof value === "number" ? formatCurrency(value) : "-"),
  },
  {
    title: "Exit",
    dataIndex: "exit_price",
    key: "exit_price",
    render: (value?: number) => (typeof value === "number" ? formatCurrency(value) : "-"),
  },
  {
    title: "PnL",
    dataIndex: "pnl",
    key: "pnl",
    render: (value?: number) => (typeof value === "number" ? formatCurrency(value) : "-"),
  },
];

const BacktestResultView = ({ result, loading, error }: BacktestResultProps) => {
  if (loading) {
    return null;
  }

  if (error) {
    return (
      <Card>
        <Typography.Text type="danger">{error}</Typography.Text>
      </Card>
    );
  }

  if (!result) {
    return (
      <Card>
        <Empty description="Run a backtest to view results" />
      </Card>
    );
  }

  type TooltipValue = number | string | Array<number | string>;

  const toNumber = (value: TooltipValue): number => {
    if (Array.isArray(value)) {
      return Number(value[0]);
    }
    return Number(value);
  };

  const currencyTooltipFormatter = (value: TooltipValue, name?: string | number) => {
    return [formatCurrency(toNumber(value)), String(name ?? "")];
  };

  const percentTooltipFormatter = (value: TooltipValue, name?: string | number, entry?: any) => {
    const dataKey = entry?.dataKey as string | undefined;
    if (dataKey === "strategyReturnArea") {
      return [null, ""];
    }
    return [formatPercent(toNumber(value)), String(name ?? "")];
  };

  const tradeTooltipFormatter = (value: TooltipValue, name?: string | number) => {
    const numeric = Math.abs(toNumber(value));
    const label = name === "buyVolume" ? "Buys" : name === "sellVolume" ? "Sells" : String(name ?? "");
    return [numeric, label];
  };

  const equityData = result.equityCurve ?? [];
  const summaryData = result.summaries ?? [];

  type TimelinePoint = {
    date: string;
    equity?: number;
    cumulativeReturn?: number;
    dailyPnl?: number;
    buyVolume?: number;
    sellVolume?: number;
    baselineEquity?: number;
    baselineCumulativeReturn?: number;
    strategyReturnArea?: number;
  };

  const timelineMap = new Map<string, TimelinePoint>();

  const ensureTimelinePoint = (date: string): TimelinePoint => {
    const existing = timelineMap.get(date);
    if (existing) {
      return existing;
    }
    const created: TimelinePoint = { date };
    timelineMap.set(date, created);
    return created;
  };

  if (equityData.length) {
    const dailySnapshots = new Map<string, typeof equityData[number]>();
    equityData.forEach((entry) => {
      const day = dayjs(entry.datetime).format("YYYY-MM-DD");
      dailySnapshots.set(day, entry);
    });
    const sortedDaily = Array.from(dailySnapshots.entries()).sort((a, b) => (a[0] > b[0] ? 1 : -1));
  let prevEquity: number | undefined;
  let firstEquity: number | undefined = Number(result.initialCapital) || undefined;
  let firstBaseline: number | undefined;
    sortedDaily.forEach(([date, entry]) => {
      const equity = Number(entry.equity ?? 0);
      const point = ensureTimelinePoint(date);
      point.equity = equity;
      if (prevEquity !== undefined && prevEquity !== 0) {
        point.dailyPnl = equity - prevEquity;
      } else {
        point.dailyPnl = 0;
      }
      if ((firstEquity === undefined || firstEquity === 0) && equity !== 0) {
        firstEquity = equity;
      }
      const equityBaseline = firstEquity ?? Number(result.initialCapital) ?? 1;
      const equityDenominator = equityBaseline !== 0 ? equityBaseline : 1;
      point.cumulativeReturn = (equity - equityDenominator) / equityDenominator;
      const baselineRaw = entry["baseline_equity"] ?? entry["baselineEquity"];
      if (baselineRaw !== undefined) {
        const baselineEquity = Number(baselineRaw) || 0;
        point.baselineEquity = baselineEquity;
        if (firstBaseline === undefined && baselineEquity !== 0) {
          firstBaseline = baselineEquity;
        }
      }
  const baselineStartCandidate = firstBaseline ?? (baselineRaw !== undefined ? Number(baselineRaw) || undefined : undefined);
  const baselineDenominator = baselineStartCandidate && baselineStartCandidate !== 0 ? baselineStartCandidate : equityDenominator;
      const baselineCurrent = (point.baselineEquity ?? baselineDenominator) || baselineDenominator;
      point.baselineCumulativeReturn = (baselineCurrent - baselineDenominator) / baselineDenominator;
      prevEquity = equity;
    });
  }

  if (result.trades?.length) {
    result.trades.forEach((trade) => {
      const timestamp = trade.timestamp ?? trade.entry_time ?? trade.exit_time;
      if (!timestamp) {
        return;
      }
      const date = dayjs(timestamp).format("YYYY-MM-DD");
      const point = ensureTimelinePoint(date);
      const quantity = Number(trade.quantity ?? 0);
      const action = (trade.action ?? "").toString().toUpperCase();
      if (action === "BUY") {
        point.buyVolume = (point.buyVolume ?? 0) + quantity;
      } else if (action === "SELL") {
        point.sellVolume = (point.sellVolume ?? 0) - quantity;
      }
    });
  }

  const timelineData = Array.from(timelineMap.values())
    .sort((a, b) => (a.date > b.date ? 1 : -1))
    .map((point) => ({
      ...point,
      cumulativeReturn: point.cumulativeReturn ?? 0,
      strategyReturnArea: point.cumulativeReturn ?? 0,
      dailyPnl: point.dailyPnl ?? 0,
      buyVolume: point.buyVolume ?? 0,
      sellVolume: point.sellVolume ?? 0,
      baselineCumulativeReturn: point.baselineCumulativeReturn ?? 0,
    }));

  const timelineChartLeftMargin = 100;

  return (
    <Card title="Backtest Results" bordered={false}>
      <Row gutter={16}>
        <Col xs={24} md={12} lg={6}>
          <Statistic title="Initial Capital" value={formatCurrency(result.initialCapital)} />
        </Col>
        <Col xs={24} md={12} lg={6}>
          <Statistic title="Ending Equity" value={formatCurrency(result.endingEquity)} />
        </Col>
        <Col xs={24} md={12} lg={6}>
          <Statistic title="Net Profit" value={formatCurrency(result.netProfit)} valueStyle={{ color: result.netProfit >= 0 ? "#3f8600" : "#cf1322" }} />
        </Col>
        <Col xs={24} md={12} lg={6}>
          <Statistic title="Return" value={formatPercent(result.returnPct)} valueStyle={{ color: result.returnPct >= 0 ? "#3f8600" : "#cf1322" }} />
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col xs={24} md={12} lg={6}>
          <Statistic title="Annualized" value={formatPercent(result.annualizedReturn)} />
        </Col>
        <Col xs={24} md={12} lg={6}>
          <Statistic title="Max Drawdown" value={formatPercent(-Math.abs(result.maxDrawdown))} valueStyle={{ color: "#cf1322" }} />
        </Col>
        <Col xs={24} md={12} lg={6}>
          <Statistic title="Trades" value={result.trades.length} />
        </Col>
        <Col xs={24} md={12} lg={6}>
          <Statistic title="Closed Trades" value={result.closedTrades.length} />
        </Col>
      </Row>

      <Divider />

      <Typography.Title level={4}>Daily Performance</Typography.Title>
      {timelineData.length ? (
        <Space direction="vertical" size={0} style={{ width: "100%" }}>
          <div style={{ width: "100%", height: 220 }}>
            <ResponsiveContainer>
              <ComposedChart data={timelineData} syncId="timeline-sync" margin={{ top: 16, right: 24, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" minTickGap={20} tickFormatter={() => ""} />
                <YAxis yAxisId="left" tickFormatter={formatPercent} width={100} orientation="left" />
                <Tooltip formatter={percentTooltipFormatter} labelFormatter={(value: string) => dayjs(value).format("YYYY-MM-DD")} />
                <Area yAxisId="left" type="monotone" dataKey="strategyReturnArea" name="" fill="rgba(22, 119, 255, 0.18)" stroke="none" isAnimationActive={false} />
                <Line yAxisId="left" type="monotone" dataKey="cumulativeReturn" name="Strategy Cumulative Return" stroke="#1677ff" dot={false} strokeWidth={2} />
                <Line yAxisId="left" type="monotone" dataKey="baselineCumulativeReturn" name="Benchmark Cumulative Return" stroke="#faad14" dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <div style={{ width: "100%", height: 220 }}>
            <ResponsiveContainer>
              <BarChart data={timelineData} syncId="timeline-sync" margin={{ top: 16, right: 24, left: timelineChartLeftMargin, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" minTickGap={20} tickFormatter={() => ""} />
                <YAxis hide />
                <Tooltip formatter={currencyTooltipFormatter} labelFormatter={(value: string) => dayjs(value).format("YYYY-MM-DD")} />
                <Bar dataKey="dailyPnl" name="Daily P&L">
                  {timelineData.map((entry) => (
                    <Cell key={`pnl-${entry.date}`} fill={entry.dailyPnl >= 0 ? "#52c41a" : "#ff4d4f"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div style={{ width: "100%", height: 220 }}>
            <ResponsiveContainer>
              <BarChart data={timelineData} syncId="timeline-sync" margin={{ top: 16, right: 24, left: timelineChartLeftMargin, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" minTickGap={20} tickFormatter={(value: string) => dayjs(value).format("MM-DD")} />
                <YAxis hide />
                <Tooltip formatter={tradeTooltipFormatter} labelFormatter={(value: string) => dayjs(value).format("YYYY-MM-DD")} />
                <Bar dataKey="buyVolume" name="Buy Volume" fill="#52c41a">
                </Bar>
                <Bar dataKey="sellVolume" name="Sell Volume" fill="#ff4d4f">
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Space>
      ) : (
        <Empty description="No timeline data" />
      )}
  <Typography.Title level={4}>P&L by Symbol</Typography.Title>
      {summaryData.length ? (
        <div style={{ width: "100%", height: 320 }}>
          <ResponsiveContainer>
            <BarChart data={summaryData} margin={{ top: 16, right: 24, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="symbol" />
              <YAxis tickFormatter={formatCurrency} width={120} />
              <Tooltip formatter={currencyTooltipFormatter} />
                <Bar dataKey="netPnl" name="P&L" radius={[4, 4, 0, 0]}>
                {summaryData.map((entry) => (
                  <Cell key={`net-${entry.symbol}`} fill={entry.netPnl >= 0 ? "#52c41a" : "#ff4d4f"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <Empty description="No summary data" />
      )}

      <Divider />

      <Typography.Title level={4}>Symbol Summaries</Typography.Title>
      <Table
        columns={summaryColumns}
        dataSource={result.summaries}
        rowKey={(record: BacktestSummary) => record.symbol}
        pagination={false}
      />

      <Divider />

      <Typography.Title level={4}>Closed Trades</Typography.Title>
      <Table
        columns={closedTradesColumns}
        dataSource={result.closedTrades}
        rowKey={(_record, index) => `closed-${index ?? 0}`}
        pagination={{ pageSize: 10 }}
        scroll={{ x: true }}
      />

      <Divider />

      <Typography.Title level={4}>Trade Log</Typography.Title>
      <Table
        columns={tradesColumns}
        dataSource={result.trades}
        rowKey={(_record, index) => `trade-${index ?? 0}`}
        pagination={{ pageSize: 10 }}
        scroll={{ x: true }}
      />

      {result.cacheFiles && result.cacheFiles.length > 0 ? (
        <>
          <Divider />
          <Typography.Title level={4}>Cached Files</Typography.Title>
          <List
            size="small"
            bordered
            dataSource={result.cacheFiles}
            renderItem={(item: string) => <List.Item>{item}</List.Item>}
          />
        </>
      ) : null}
    </Card>
  );
};

export default BacktestResultView;

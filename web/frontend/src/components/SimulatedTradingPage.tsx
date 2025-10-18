import axios from "axios";
import dayjs from "dayjs";
import { useCallback, useMemo, useState } from "react";
import {
  Button,
  Card,
  Col,
  Divider,
  Form,
  Input,
  InputNumber,
  Radio,
  Row,
  Space,
  Table,
  Tag,
  Typography,
  Switch,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { createSimulatedOrder, fetchPortfolioSnapshot, fetchSimulatedOrders } from "../api";
import type { CreateSimulatedOrderPayload, PortfolioPosition, PortfolioSnapshot, SimulatedOrder } from "../types";

const helperCards = [
  {
    title: "Portfolio Tracker",
    description:
      "Monitor paper account balances, open positions, and realized P&L in real time.",
    command: "python -m quant_trading.core.portfolio_tracker",
  },
  {
    title: "Market Data Tracker",
    description:
      "Stream live quotes and maintain 1/3/5/10 minute MACD-enriched bars for strategy inputs.",
    command: "python -m quant_trading.data.market_data_tracker",
  },
  {
    title: "Backtest Engine",
    description:
      "Re-run historical simulations to validate changes before mirroring them in paper trades.",
    command: "python -m quant_trading.backtesting.run_backtest --timeframe 5m --data-dir market_data",
  },
  {
    title: "Custom Scripts",
    description:
      "Leverage your own automation via quant_trading.core.order_manager to stage paper orders.",
    command: "python -m quant_trading.core.order_manager",
  },
];

const columns: ColumnsType<SimulatedOrder> = [
  {
    title: "Symbol",
    dataIndex: "symbol",
    key: "symbol",
    render: (value: string) => value.toUpperCase(),
  },
  {
    title: "Side",
    dataIndex: "side",
    key: "side",
    render: (value: SimulatedOrder["side"]) => (
      <Tag color={value === "BUY" ? "green" : "red"}>{value}</Tag>
    ),
  },
  {
    title: "Quantity",
    dataIndex: "quantity",
    key: "quantity",
    width: 110,
    align: "right",
  },
  {
    title: "Type",
    dataIndex: "orderType",
    key: "orderType",
  },
  {
    title: "Fill Price",
    dataIndex: "fillPrice",
    key: "fillPrice",
    align: "right",
    render: (value: SimulatedOrder["fillPrice"]) => (value == null ? "-" : `$${value.toFixed(2)}`),
  },
  {
    title: "Created",
    dataIndex: "createdAt",
    key: "createdAt",
    render: (value: string) => dayjs(value).format("YYYY-MM-DD HH:mm"),
  },
  {
    title: "Notes",
    dataIndex: "notes",
    key: "notes",
    ellipsis: true,
  },
];

const formatMoney = (value?: number | null, currency?: string): string => {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  const prefix = currency ? `${currency} ` : "$";
  return `${prefix}${value.toFixed(2)}`;
};

const formatPercent = (value?: number | null): string => {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  return `${(value * 100).toFixed(2)}%`;
};

const formatNumber = (value?: number | null): string => {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
};

const positionColumns: ColumnsType<PortfolioPosition> = [
  {
    title: "Symbol",
    dataIndex: "symbol",
    key: "symbol",
    render: (value?: string) => value?.toUpperCase() ?? "-",
    fixed: "left",
  },
  {
    title: "Qty",
    dataIndex: "position",
    key: "position",
    align: "right",
    render: (value: PortfolioPosition["position"]) => formatNumber(value),
  },
  {
    title: "Avg Cost",
    dataIndex: "avgCost",
    key: "avgCost",
    align: "right",
    render: (value: PortfolioPosition["avgCost"], record) => formatMoney(value, record.currency),
  },
  {
    title: "Market Price",
    dataIndex: "marketPrice",
    key: "marketPrice",
    align: "right",
    render: (value: PortfolioPosition["marketPrice"], record) => formatMoney(value, record.currency),
  },
  {
    title: "Market Value",
    dataIndex: "marketValue",
    key: "marketValue",
    align: "right",
    render: (value: PortfolioPosition["marketValue"], record) => formatMoney(value, record.currency),
  },
  {
    title: "Daily P&L",
    dataIndex: "dailyPnl",
    key: "dailyPnl",
    align: "right",
    render: (value: PortfolioPosition["dailyPnl"], record) => {
      const formatted = formatMoney(value, record.currency);
      if (value == null || value === 0) {
        return formatted;
      }
      return <Typography.Text type={value > 0 ? "success" : "danger"}>{formatted}</Typography.Text>;
    },
  },
  {
    title: "Unrealized P&L",
    dataIndex: "unrealizedPnl",
    key: "unrealizedPnl",
    align: "right",
    render: (value: PortfolioPosition["unrealizedPnl"], record) => {
      const formatted = formatMoney(value, record.currency);
      if (value == null || value === 0) {
        return formatted;
      }
      return <Typography.Text type={value > 0 ? "success" : "danger"}>{formatted}</Typography.Text>;
    },
  },
  {
    title: "Unrealized %",
    dataIndex: "unrealizedPnlRatio",
    key: "unrealizedPnlRatio",
    align: "right",
    render: (value: PortfolioPosition["unrealizedPnlRatio"]) => formatPercent(value),
  },
  {
    title: "Realized P&L",
    dataIndex: "realizedPnl",
    key: "realizedPnl",
    align: "right",
    render: (value: PortfolioPosition["realizedPnl"], record) => {
      const formatted = formatMoney(value, record.currency);
      if (value == null || value === 0) {
        return formatted;
      }
      return <Typography.Text type={value > 0 ? "success" : "danger"}>{formatted}</Typography.Text>;
    },
  },
];

const SimulatedTradingPage = () => {
  const [orders, setOrders] = useState<SimulatedOrder[]>([]);
  const [loadingOrders, setLoadingOrders] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [ibkrConnected, setIbkrConnected] = useState<boolean>(false);
  const [portfolio, setPortfolio] = useState<PortfolioSnapshot | null>(null);
  const [loadingPortfolio, setLoadingPortfolio] = useState<boolean>(false);
  const [form] = Form.useForm<CreateSimulatedOrderPayload>();

  const openOrderCount = useMemo(() => orders.filter((order) => order.status !== "FILLED").length, [orders]);

  const positionSummary = useMemo(() => {
    if (!portfolio?.positions.length) {
      return [] as Array<{ currency: string; marketValue: number; dailyPnl: number; unrealizedPnl: number; realizedPnl: number }>;
    }
    const summaryMap = new Map<string, { currency: string; marketValue: number; dailyPnl: number; unrealizedPnl: number; realizedPnl: number }>();
    portfolio.positions.forEach((item) => {
      const currency = item.currency || "USD";
      const existing = summaryMap.get(currency) || {
        currency,
        marketValue: 0,
        dailyPnl: 0,
        unrealizedPnl: 0,
        realizedPnl: 0,
      };
      existing.marketValue += item.marketValue ?? 0;
      existing.dailyPnl += item.dailyPnl ?? 0;
      existing.unrealizedPnl += item.unrealizedPnl ?? 0;
      existing.realizedPnl += item.realizedPnl ?? 0;
      summaryMap.set(currency, existing);
    });
    return Array.from(summaryMap.values());
  }, [portfolio]);

  const getErrorMessage = useCallback((err: unknown) => {
    if (axios.isAxiosError(err)) {
      return err.response?.data?.detail || err.message;
    }
    return (err as Error).message;
  }, []);

  const loadOrders = useCallback(async () => {
    setLoadingOrders(true);
    try {
      const data = await fetchSimulatedOrders();
      setOrders(data);
    } catch (err: unknown) {
      message.error(`Failed to load simulated orders: ${getErrorMessage(err)}`);
    } finally {
      setLoadingOrders(false);
    }
  }, [getErrorMessage]);

  const loadPortfolio = useCallback(async () => {
    setLoadingPortfolio(true);
    try {
      const data = await fetchPortfolioSnapshot();
      setPortfolio(data);
    } catch (err: unknown) {
      message.error(`Failed to load portfolio: ${getErrorMessage(err)}`);
    } finally {
      setLoadingPortfolio(false);
    }
  }, [getErrorMessage]);

  const handleSubmit = useCallback(
    async (values: CreateSimulatedOrderPayload) => {
      const payload: CreateSimulatedOrderPayload = {
        ...values,
        symbol: values.symbol.trim().toUpperCase(),
        price: Number(values.price),
        notes: values.notes?.trim(),
      };

      setSubmitting(true);
      try {
        await createSimulatedOrder(payload);
        message.success("Simulated order recorded");
        form.resetFields(["symbol", "quantity", "price", "notes"]);
        await loadOrders();
      } catch (err: unknown) {
        message.error(`Failed to record order: ${getErrorMessage(err)}`);
      } finally {
        setSubmitting(false);
      }
    },
    [form, loadOrders]
  );

  const handleToggleConnection = useCallback(
    (checked: boolean) => {
      setIbkrConnected(checked);
      if (checked) {
        message.success("IBKR connection enabled (paper trading mode)");
        void loadPortfolio();
      } else {
        message.info("IBKR connection disabled");
        setPortfolio(null);
      }
    },
    [loadPortfolio]
  );

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Row gutter={[24, 24]} align="top">
        <Col xs={24} lg={10} xl={8}>
          <Space direction="vertical" size="large" style={{ width: "100%" }}>
            <Card title="IBKR Connection" bordered={false}
              extra={<Tag color={ibkrConnected ? "green" : "default"}>{ibkrConnected ? "Connected" : "Offline"}</Tag>}
            >
              <Space direction="vertical" size="middle" style={{ width: "100%" }}>
                <Space align="center">
                  <Switch checked={ibkrConnected} onChange={handleToggleConnection} />
                  <Typography.Text>
                    {ibkrConnected ? "Paper account link active on port 7497" : "Toggle on to initiate paper session"}
                  </Typography.Text>
                </Space>
                <Typography.Paragraph type="secondary">
                  Flip the switch to manually manage the TWS paper connection. Keep it off when rehearsing without market
                  connectivity.
                </Typography.Paragraph>
              </Space>
            </Card>

            <Card title="Log Simulated Order" bordered={false}>
              <Form<CreateSimulatedOrderPayload> layout="vertical" form={form} onFinish={handleSubmit} initialValues={{
                side: "BUY",
                orderType: "MARKET",
              }}>
                <Form.Item
                  label="Symbol"
                  name="symbol"
                  rules={[{ required: true, message: "Enter the traded symbol" }]}
                >
                  <Input placeholder="e.g. AAPL" maxLength={12} autoComplete="off" />
                </Form.Item>

                <Form.Item label="Side" name="side" rules={[{ required: true }]}>
                  <Radio.Group buttonStyle="solid">
                    <Radio.Button value="BUY">Buy</Radio.Button>
                    <Radio.Button value="SELL">Sell</Radio.Button>
                  </Radio.Group>
                </Form.Item>

                <Form.Item
                  label="Quantity"
                  name="quantity"
                  rules={[{ required: true, message: "Enter the quantity" }]}
                >
                  <InputNumber style={{ width: "100%" }} min={1} max={1_000_000} step={1} />
                </Form.Item>

                <Form.Item
                  label="Execution Price"
                  name="price"
                  rules={[{ required: true, message: "Enter the execution price" }]}
                >
                  <InputNumber style={{ width: "100%" }} min={0} step={0.01} prefix="$" />
                </Form.Item>

                <Form.Item label="Order Type" name="orderType" rules={[{ required: true }]}
                >
                  <Radio.Group buttonStyle="solid">
                    <Radio.Button value="MARKET">Market</Radio.Button>
                    <Radio.Button value="LIMIT">Limit</Radio.Button>
                    <Radio.Button value="STOP">Stop</Radio.Button>
                  </Radio.Group>
                </Form.Item>

                <Form.Item label="Notes" name="notes">
                  <Input.TextArea rows={3} placeholder="Optional context (strategy signal, rationale, risk notes)" />
                </Form.Item>

                <Form.Item>
                  <Space>
                    <Button type="primary" htmlType="submit" loading={submitting} disabled={submitting}>
                      Record Order
                    </Button>
                    <Button onClick={() => void loadOrders()} disabled={loadingOrders}>
                      Refresh Orders
                    </Button>
                  </Space>
                </Form.Item>
              </Form>
            </Card>
          </Space>
        </Col>
        <Col xs={24} lg={14} xl={16}>
          <Card
            title="Portfolio Snapshot"
            bordered={false}
            extra={
              <Space>
                {portfolio && (
                  <Typography.Text type="secondary">
                    As of {dayjs(portfolio.retrievedAt).format("YYYY-MM-DD HH:mm:ss")}
                  </Typography.Text>
                )}
                <Button
                  type="link"
                  onClick={() => void loadPortfolio()}
                  disabled={!ibkrConnected}
                  loading={loadingPortfolio}
                >
                  Refresh
                </Button>
              </Space>
            }
            style={{ marginBottom: 24 }}
          >
            {portfolio ? (
              <Space direction="vertical" size="middle" style={{ width: "100%" }}>
                <div>
                  <Typography.Text strong>Cash Balances</Typography.Text>
                  {portfolio.cashBalances.length ? (
                    portfolio.cashBalances.map((balance) => (
                      <Typography.Paragraph key={balance.label} style={{ marginBottom: 8 }}>
                        {balance.label}: {balance.amounts
                          .map((amount) => {
                            const formatted = amount.value != null ? amount.value.toFixed(2) : amount.raw ?? "-";
                            return `${amount.currency} ${formatted}`;
                          })
                          .join(" · ")}
                      </Typography.Paragraph>
                    ))
                  ) : (
                    <Typography.Paragraph type="secondary">No cash data</Typography.Paragraph>
                  )}
                </div>

                <div>
                  <Typography.Text strong>Open Positions</Typography.Text>
                  {portfolio.positions.length ? (
                    <>
                      {positionSummary.length > 0 && (
                        <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
                          {positionSummary
                            .map(
                              (summary) =>
                                `Exposure ${formatMoney(summary.marketValue, summary.currency)} · Daily P&L ${formatMoney(summary.dailyPnl, summary.currency)} · Unrealized P&L ${formatMoney(summary.unrealizedPnl, summary.currency)}`
                            )
                            .join("  |  ")}
                        </Typography.Paragraph>
                      )}
                      <Table<PortfolioPosition>
                        rowKey={(record, index) => `${record.symbol ?? "UNKNOWN"}-${index}`}
                        columns={positionColumns}
                        dataSource={portfolio.positions}
                        pagination={false}
                        size="small"
                        scroll={{ x: 960 }}
                      />
                    </>
                  ) : (
                    <Typography.Paragraph type="secondary">No open positions</Typography.Paragraph>
                  )}
                </div>

                <div>
                  <Typography.Text strong>Market Value by Currency</Typography.Text>
                  {portfolio.marketValueByCurrency.length ? (
                    portfolio.marketValueByCurrency.map((item) => (
                      <Typography.Paragraph key={item.currency} style={{ marginBottom: 8 }}>
                        {item.currency}: ${item.marketValue.toFixed(2)}
                      </Typography.Paragraph>
                    ))
                  ) : (
                    <Typography.Paragraph type="secondary">No holdings recorded</Typography.Paragraph>
                  )}
                </div>
              </Space>
            ) : (
              <Typography.Paragraph type="secondary">
                Enable the IBKR connection switch to load real-time portfolio balances.
              </Typography.Paragraph>
            )}
          </Card>

          <Card
            title="Recent Simulated Orders"
            bordered={false}
            extra={
              <Typography.Text type="secondary">
                {openOrderCount} open · {orders.length} logged
              </Typography.Text>
            }
          >
            <Typography.Paragraph type="secondary" style={{ marginBottom: 16 }}>
              Use the refresh button to pull the latest blotter entries on demand.
            </Typography.Paragraph>
            <Table<SimulatedOrder>
              rowKey="id"
              dataSource={orders}
              columns={columns}
              loading={loadingOrders}
              pagination={{ pageSize: 8, showSizeChanger: false }}
            />
          </Card>
        </Col>
      </Row>

      <Divider orientation="left">Key Console Helpers</Divider>

      <Row gutter={[24, 24]}>
        {helperCards.map((item) => (
          <Col xs={24} md={12} key={item.title}>
            <Card title={item.title} bordered={false}>
              <Typography.Paragraph>{item.description}</Typography.Paragraph>
              <Typography.Paragraph>
                <Typography.Text code>{item.command}</Typography.Text>
              </Typography.Paragraph>
            </Card>
          </Col>
        ))}
      </Row>
    </Space>
  );
};

export default SimulatedTradingPage;

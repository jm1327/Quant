import { useCallback, useEffect, useState } from "react";
import { Button, Layout, Row, Col, Space, Spin, Typography, message } from "antd";
import axios from "axios";
import BacktestForm from "./components/BacktestForm";
import BacktestResult from "./components/BacktestResult";
import SimulatedTradingPage from "./components/SimulatedTradingPage";
import { fetchStrategies, runBacktest } from "./api";
import type { BacktestFormValues, BacktestResponse } from "./types";

const { Header, Content, Footer } = Layout;

const App = () => {
  const [activeView, setActiveView] = useState<"backtest" | "simulated">("backtest");
  const [strategies, setStrategies] = useState<string[]>([]);
  const [defaultSymbols, setDefaultSymbols] = useState<string[]>([]);
  const [loadingStrategies, setLoadingStrategies] = useState<boolean>(true);
  const [result, setResult] = useState<BacktestResponse>();
  const [loadingBacktest, setLoadingBacktest] = useState<boolean>(false);
  const [error, setError] = useState<string>();

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchStrategies();
        setStrategies(data.strategies);
        setDefaultSymbols(data.defaultSymbols);
      } catch (err: unknown) {
        const messageText = axios.isAxiosError(err)
          ? err.response?.data?.detail || err.message
          : (err as Error).message;
        setError(messageText);
        message.error(`Failed to load strategies: ${messageText}`);
      } finally {
        setLoadingStrategies(false);
      }
    };

    load();
  }, []);

  const handleRunBacktest = useCallback(
    async (values: BacktestFormValues) => {
      setLoadingBacktest(true);
      setError(undefined);
      try {
        const data = await runBacktest(values);
        setResult(data);
        message.success("Backtest completed successfully");
      } catch (err: unknown) {
        const messageText = axios.isAxiosError(err)
          ? err.response?.data?.detail || err.message
          : (err as Error).message;
        setError(messageText);
        message.error(messageText);
      } finally {
        setLoadingBacktest(false);
      }
    },
    []
  );

  const isBacktestView = activeView === "backtest";

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header style={{ background: "#001529" }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Typography.Title level={3} style={{ color: "#fff", margin: 0 }}>
              Quant Trading Dashboard
            </Typography.Title>
          </Col>
          <Col>
            <Space>
              <Button
                type={isBacktestView ? "primary" : "default"}
                ghost
                onClick={() => setActiveView("backtest")}
              >
                Backtest
              </Button>
              <Button
                type={!isBacktestView ? "primary" : "default"}
                ghost
                onClick={() => setActiveView("simulated")}
              >
                Simulated Trading
              </Button>
            </Space>
          </Col>
        </Row>
      </Header>

      <Content style={{ padding: "24px", maxWidth: 1400, margin: "0 auto", width: "100%" }}>
        {isBacktestView ? (
          loadingStrategies ? (
            <Space direction="vertical" style={{ width: "100%", alignItems: "center" }}>
              <Spin tip="Loading strategies..." />
            </Space>
          ) : (
            <Row gutter={[24, 24]} align="top">
              <Col xs={24} lg={10} xl={8} style={{ display: "flex" }}>
                <BacktestForm
                  strategies={strategies}
                  defaultSymbols={defaultSymbols}
                  loading={loadingBacktest}
                  onSubmit={handleRunBacktest}
                />
              </Col>
              <Col xs={24} lg={14} xl={16}>
                <BacktestResult result={result} loading={loadingBacktest} error={error} />
              </Col>
            </Row>
          )
        ) : (
          <SimulatedTradingPage />
        )}
      </Content>

      <Footer style={{ textAlign: "center" }}>
        Quant Trading Platform © {new Date().getFullYear()}
      </Footer>
    </Layout>
  );
};

export default App;

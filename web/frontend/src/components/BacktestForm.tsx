import { useEffect } from "react";
import { Button, Card, DatePicker, Form, InputNumber, Select, Space, Switch, Typography } from "antd";
import type { Dayjs } from "dayjs";
import type { BacktestFormValues } from "../types";

interface BacktestFormProps {
  strategies: string[];
  defaultSymbols: string[];
  loading: boolean;
  onSubmit: (values: BacktestFormValues) => void;
}

interface FormShape {
  strategy: string;
  symbols: string[];
  timeframe: string;
  start?: Dayjs;
  end?: Dayjs;
  initialCapital?: number;
  commission?: number;
  writeCache: boolean;
}

const TIMEFRAME_OPTIONS = ["1m", "3m", "5m", "10m", "15m", "30m", "60m"];

const BacktestForm = ({ strategies, defaultSymbols, loading, onSubmit }: BacktestFormProps) => {
  const [form] = Form.useForm<FormShape>();

  useEffect(() => {
    if (strategies.length && !form.getFieldValue("strategy")) {
      form.setFieldsValue({
        strategy: strategies[0],
        symbols: defaultSymbols,
        timeframe: "5m",
        writeCache: true,
      });
    }
  }, [strategies, defaultSymbols, form]);

  const handleSubmit = (values: FormShape) => {
    const payload: BacktestFormValues = {
      strategy: values.strategy,
      symbols: values.symbols,
      timeframe: values.timeframe,
      start: values.start ? values.start.format("YYYY-MM-DD") : undefined,
      end: values.end ? values.end.format("YYYY-MM-DD") : undefined,
      initialCapital: values.initialCapital,
      commission: values.commission,
      writeCache: values.writeCache,
    };
    onSubmit(payload);
  };

  return (
    <Card title="Run Backtest" bordered={false}>
      <Form<FormShape> form={form} layout="vertical" onFinish={handleSubmit}>
        <Form.Item label="Strategy" name="strategy" rules={[{ required: true, message: "Select a strategy" }]}>
          <Select placeholder="Select strategy" options={strategies.map((value) => ({ value, label: value }))} allowClear={false} />
        </Form.Item>

        <Form.Item
          label="Symbols"
          name="symbols"
          rules={[{ required: true, message: "Choose at least one symbol" }]}
        >
          <Select
            mode="multiple"
            allowClear
            optionFilterProp="label"
            placeholder="Select symbols"
            options={defaultSymbols.map((symbol) => ({ value: symbol, label: symbol }))}
          />
        </Form.Item>

        <Form.Item label="Timeframe" name="timeframe" rules={[{ required: true, message: "Select timeframe" }]}>
          <Select options={TIMEFRAME_OPTIONS.map((value) => ({ value, label: value }))} />
        </Form.Item>

        <Space direction="horizontal" size="large" style={{ width: "100%" }}>
          <Form.Item label="Start" name="start" style={{ flex: 1 }}>
            <DatePicker
              style={{ width: "100%" }}
              allowClear
              format="YYYY-MM-DD"
              disabledDate={(current: Dayjs | null) => !!form.getFieldValue("end") && !!current && current > form.getFieldValue("end")}
            />
          </Form.Item>

          <Form.Item label="End" name="end" style={{ flex: 1 }}>
            <DatePicker
              style={{ width: "100%" }}
              allowClear
              format="YYYY-MM-DD"
              disabledDate={(current: Dayjs | null) => !!form.getFieldValue("start") && !!current && current < form.getFieldValue("start")}
            />
          </Form.Item>
        </Space>

        <Space direction="horizontal" size="large" style={{ width: "100%" }}>
          <Form.Item label="Initial Capital" name="initialCapital" style={{ flex: 1 }}>
            <InputNumber style={{ width: "100%" }} min={0} step={1000} prefix="$" placeholder="Default strategy value" />
          </Form.Item>

          <Form.Item label="Commission" name="commission" style={{ flex: 1 }}>
            <InputNumber style={{ width: "100%" }} min={0} step={0.01} prefix="$" placeholder="Default strategy value" />
          </Form.Item>
        </Space>

        <Form.Item
          label="Write Cache"
          name="writeCache"
          valuePropName="checked"
          tooltip="Stores results under backtest_results for offline review"
        >
          <Switch />
        </Form.Item>

        <Form.Item shouldUpdate>
          {() => (
            <Button type="primary" htmlType="submit" loading={loading} disabled={loading}>
              Run Backtest
            </Button>
          )}
        </Form.Item>

        <Typography.Paragraph type="secondary">
          Dates are optional; defaults to the last two years of available data when omitted.
        </Typography.Paragraph>
      </Form>
    </Card>
  );
};

export default BacktestForm;

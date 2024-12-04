export enum MessageType {
  ORDER_CREATED = "ORDER_CREATED",
  ORDER_ACKNOWLEDGED = "ORDER_ACKNOWLEDGED",
  DOENER_ASSIGNED = "DOENER_ASSIGNED",
  INVOICE_CREATED = "INVOICE_CREATED",
}

export type Message = {
  correlation_id: string;
  error: Error | null;
  message_type: MessageType;
  order_id: string;
  payload: { shop?: Shop; price?: number; status: string };
  timestamp: string;
  version: string;
};

export type Shop = {
  id: string;
  name: string;
  price: number;
};

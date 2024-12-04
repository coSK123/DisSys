"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import validator from "validator";
import { z } from "zod";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "./ui/form";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Message, MessageType } from "@/types/Message";

const formSchema = z.object({
  personalInformation: z.object({
    name: z.string().min(3),
    email: z.string().email(),
    phone: z.string().refine(validator.isMobilePhone),
  }),
});

export default function DoenerForm({
  addUpdate,
}: {
  addUpdate: (update: Message) => void;
}) {
  const form = useForm<z.infer<typeof formSchema>>({
    mode: "onBlur",
    resolver: zodResolver(formSchema),
    defaultValues: {
      personalInformation: {
        name: "",
        email: "",
        phone: "",
      },
    },
  });

  const connect = (orderId: string) => {
    const ws = new WebSocket(`ws://localhost:8080/ws/${orderId}`);

    ws.onmessage = function (event) {
      const update = JSON.parse(event.data);
      addUpdate(update);
    };

    ws.onclose = function () {
      console.log("WebSocket connection closed");
    };

    ws.onerror = function (error) {
      console.error("WebSocket error:", error);
    };
  };

  const placeOrder = async () => {
    const customerId = "PLACEHOLDER_CUSTOMER_ID";

    try {
      const response = await fetch("http://localhost:8080/order/doener", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          customer_id: customerId,
          details: {
            notes: "Mit Alles und scharf",
          },
        }),
      });

      const data = await response.json();
      console.log("Order placed:", data);

      // Connect to WebSocket for updates
      connect(data.order_id);
      // Add initial update
      addUpdate({
        correlation_id: "PLACEHOLDER_CORRELATION_ID",
        message_type: MessageType.ORDER_CREATED,
        order_id: data.order_id as string,
        error: null,
        timestamp: new Date().toISOString(),
        payload: {
          status: "Order placed successfully",
        },
        version: "0.0",
      });
    } catch (error) {
      console.error("Error placing order:", error);
    }
  };

  function onSubmit(values: z.infer<typeof formSchema>) {
    console.log(values);
    placeOrder();
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="space-y-4 flex flex-col grow p-4"
      >
        <h1 className="text-2xl font-bold">Persöhnliche Daten</h1>
        <div className="space-y-2 my-2">
          <FormField
            control={form.control}
            name="personalInformation.name"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm font-bold text-gray-800">
                  Vor- und Zuname
                </FormLabel>
                <FormControl>
                  <Input
                    className="w-full h-12"
                    placeholder="Trage deinen Vor- und Zunamen ein"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="personalInformation.email"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm font-bold text-gray-800">
                  E-mail
                </FormLabel>
                <FormControl>
                  <Input
                    className="w-full h-12"
                    placeholder="deinname@email.de"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="personalInformation.phone"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm font-bold text-gray-800">
                  Telefonnummer
                </FormLabel>
                <FormControl>
                  <Input
                    className="w-full h-12"
                    placeholder="Trage deine Telefonnummer ein"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <Button
          type="submit"
          className="h-12 rounded-full text-xl font-bold bg-orange-600 hover:bg-orange-700 active:bg-orange-800 text-white"
        >
          Kostenpflichtig bestellen
        </Button>
      </form>
    </Form>
  );
}

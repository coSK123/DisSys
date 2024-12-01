"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
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
import validator from "validator";

const enum ShippingType {
  DELIVERY = "delivery",
  PICKUP = "pickup",
}

const formSchema = (shippingType: ShippingType) =>
  z.object({
    address:
      shippingType === ShippingType.DELIVERY
        ? z.object({
            street: z.string(),
            houseNumber: z.string(),
            postalCode: z.string(),
            city: z.string().min(3),
          })
        : z.object({}),
    personalInformation: z.object({
      name: z.string().min(3),
      email: z.string().email(),
      phone: z.string().refine(validator.isMobilePhone),
    }),
  });

export default function ContactForm() {
  const shippingType = ShippingType.PICKUP;
  const form = useForm<z.infer<ReturnType<typeof formSchema>>>({
    mode: "onBlur",
    resolver: zodResolver(formSchema(shippingType)),
    defaultValues: {
      address: {
        street: "",
        houseNumber: "",
        postalCode: "",
        city: "",
      },
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
    const customerId = "CUST123";

    try {
      const response = await fetch("http://localhost:8080/order/doener", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          customer_id: customerId,
          details: {
            notes: "Extra sauce please",
          },
        }),
      });

      const data = await response.json();
      console.log("Order placed:", data);

      // Connect to WebSocket for updates
      connect(data.order_id);

      // Add initial update
      addUpdate({
        message_type: "ORDER_CREATED",
        order_id: data.order_id,
        timestamp: new Date().toISOString(),
        payload: {
          status: "Order placed successfully",
        },
      });
    } catch (error) {
      console.error("Error placing order:", error);
    }
  };

  const addUpdate = (update: {
    message_type: string;
    order_id: string;
    timestamp: string;
    payload: { status: string };
  }) => {
    console.log("New update:", update);
  };

  function onSubmit(values: z.infer<ReturnType<typeof formSchema>>) {
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
          Bestellen und bezahlen
        </Button>
      </form>
    </Form>
  );
}

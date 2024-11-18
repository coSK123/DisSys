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

  function onSubmit(values: z.infer<ReturnType<typeof formSchema>>) {
    console.log(values);
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

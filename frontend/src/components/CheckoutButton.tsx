"use client";

import { ShoppingBasket } from "lucide-react";
import { Button } from "./ui/button";
import { OrderItem } from "@/types/Order";

export default function CheckoutButton({
  cart,
  updateCart,
}: {
  cart: OrderItem[];
  updateCart: (cart: OrderItem[]) => void;
}) {
  if (cart === null) {
    return null;
  }

  const formatter = new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
  });

  const total = cart.reduce(
    (acc: number, item: { food: { price: number }; quantity: number }) =>
      acc + item.food.price * item.quantity,
    0
  );

  const totalFormatted = formatter.format(total);
  return (
    <div className="sticky bottom-0 rounded-t-lg w-full outline outline-gray-200 outline-1 px-2 pt-2 pb-8">
      <Button className="w-full min-h-12 rounded-full bg-orange-600 hover:bg-orange-700 active:bg-orange-800 space-x-1">
        <ShoppingBasket style={{ width: "1.5rem", height: "1.5rem" }} />
        <h2 className="text-xl font-bold">Warenkorb ({totalFormatted})</h2>
      </Button>
    </div>
  );
}

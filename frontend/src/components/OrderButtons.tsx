"use client";

import { Minus, Plus } from "lucide-react";
import { Button } from "./ui/button";
import { useState } from "react";
import { Food } from "@/types/Food";
import { DialogClose } from "./ui/dialog";
import { OrderItem } from "@/types/Order";

export default function OrderButtons({
  food,
  cart,
  updateCart,
}: {
  food: Food;
  cart: OrderItem[];
  updateCart: (cart: OrderItem[]) => void;
}) {
  const [quantity, setQuantity] = useState(1);
  const formatter = new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
  });

  const onAddToCart = () => {
    const product = { food: food, quantity: quantity };
    if (cart.length === 0) {
      updateCart([product]);
      return;
    }

    const existing = cart.find((item: OrderItem) => item.food.id === food.id);
    if (existing) {
      existing.quantity += quantity;
      updateCart([...cart]);
      return;
    }
    cart.push(product);
    updateCart([...cart]);
  };

  return (
    <div className="flex p-4 justify-around space-x-2">
      <div className="flex justify-between items-center bg-black/[.04] rounded-full space-x-3">
        <Button
          variant="ghost"
          className="p-4 rounded-full size-10 hover:bg-black/[.08]"
          onClick={() => setQuantity((prev) => Math.max(1, prev - 1))}
          disabled={quantity <= 1}
        >
          <Minus style={{ width: "1.5rem", height: "1.5rem" }} />
        </Button>
        <span className="w-[2ch] text-center font-bold text-xl">
          {quantity}
        </span>
        <Button
          variant="ghost"
          className="p-4 rounded-full size-10 hover:bg-black/[.08]"
          onClick={() => setQuantity((prev) => prev + 1)}
        >
          <Plus style={{ width: "1.5rem", height: "1.5rem" }} />
        </Button>
      </div>
      <DialogClose asChild>
        <Button
          className="grow h-full rounded-full bg-orange-600 hover:bg-orange-700 active:bg-orange-800 text-xl font-bold"
          onClick={onAddToCart}
        >
          {formatter.format(food.price * quantity)}
        </Button>
      </DialogClose>
    </div>
  );
}

"use client";

import { Message, MessageType, Shop } from "@/types/Message";
import { useState } from "react";
import DoenerForm from "./DoenerForm";
import Image from "next/image";
import { BadgeCheck, Info } from "lucide-react";
import { Progress } from "./ui/progress";

export default function DoenerUpdates() {
  const [update, setUpdate] = useState<Message | null>();
  const [shop, setShop] = useState<Shop | null>();

  const formatter = new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
  });

  const addUpdate = (update: Message) => {
    setUpdate(update);
    if (update.message_type === MessageType.DOENER_ASSIGNED)
      setShop(update.payload.shop);
    console.log(update);
  };

  const renderProgress = () => {
    switch (update?.message_type) {
      case MessageType.ORDER_CREATED:
        return 25;
      case MessageType.ORDER_ACKNOWLEDGED:
        return 50;
      case MessageType.DOENER_ASSIGNED:
        return 75;
      case MessageType.INVOICE_CREATED:
        return 100;
      default:
        return;
    }
  };

  const renderProgressMessage = () => {
    switch (update?.message_type) {
      case MessageType.ORDER_CREATED:
        return "Bestellung aufgegeben";
      case MessageType.ORDER_ACKNOWLEDGED:
        return "Bestellung angenommen";
      case MessageType.DOENER_ASSIGNED:
        return "Dönerladen gefunden";
      case MessageType.INVOICE_CREATED:
        return "Rechnung erstellt";
      default:
        return;
    }
  };

  return (
    <div>
      {!update ? (
        <>
          <div className="p-4 space-y-2 flex flex-col">
            <Image
              src="/kebab.png"
              alt="Bild eines Döners"
              width={720}
              height={720}
              className="self-center"
            />
            <h1 className="text-2xl font-bold">Bestelle deinen Döner!</h1>
            <p>
              Gib deine persönlichen Daten ein und erfahre den Standort deines
              Dönerladens.
            </p>
          </div>
          <DoenerForm addUpdate={addUpdate} />
        </>
      ) : (
        <div className="flex flex-col items-center divide-y">
          <BadgeCheck className="size-72 text-green-500 p-4" />
          <div className="p-4 w-full flex flex-col items-center space-y-4">
            <h1 className="text-lg font-normal">{renderProgressMessage()}</h1>
            <Progress value={renderProgress()} className="w-full" />
          </div>
          {[MessageType.DOENER_ASSIGNED, MessageType.INVOICE_CREATED].includes(
            update.message_type
          ) && (
            <div className="space-y-2 w-full p-4">
              <h1 className="text-2xl font-bold">Dein Dönerladen</h1>
              <div>
                {shop?.name}: {formatter.format(shop?.price as number)}
              </div>
            </div>
          )}
        </div>
      )}
      {update?.message_type === MessageType.INVOICE_CREATED && (
        <div className="p-4 m-4 rounded-lg bg-orange-200 flex space-x-4 items-start">
          <Info className="size-10" />
          <div className="space-y-1 flex flex-col">
            <h1 className="text-xl font-bold">
              Vielen Dank für deine Bestellung!
            </h1>
            <p>
              Deine Rechnung wurde dir per E-Mail zugeschickt. Wir freuen uns
              auf deinen nächsten Besuch!
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

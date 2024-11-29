import ContactForm from "@/components/ContactForm";
import Header from "@/components/Header";

export default function CheckoutPage() {
  return (
    <div className="">
      <Header heading="Kasse" href="/order" />
      <div className="flex flex-col lg:flex-row">
        <ContactForm />
        <div className="bg-black w-80"></div>
      </div>
    </div>
  );
}

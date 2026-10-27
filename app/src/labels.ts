// Every label is shown in English with a Hinglish line under it.
// Labels are words only — amounts and dates always come from the API.
export type Label = { en: string; hi: string };

export const L = {
  title: { en: 'My next payment', hi: 'Meri agli payment' },
  phone: { en: 'Phone number', hi: 'Apna phone number daalein' },
  check: { en: 'Check', hi: 'Check karein' },
  enterPhone: { en: 'Please enter your phone number', hi: 'Pehle apna phone number daalein' },
  loading: { en: 'Checking your payments…', hi: 'Aapki payments check ho rahi hain…' },
  nextPayment: { en: 'Next payment', hi: 'Agli payment' },
  trip: { en: 'Trip', hi: 'Trip' },
  amount: { en: 'Amount (₹)', hi: 'Rakam (₹)' },
  dueDate: { en: 'Due date', hi: 'Aakhri tareekh' },
  overdue: { en: 'OVERDUE', hi: 'Due date nikal gayi' },
  overdueNote: {
    en: 'This payment is past its due date. Please pay it first.',
    hi: 'Is payment ki due date nikal chuki hai. Pehle yeh payment karein.',
  },
  upcoming: { en: 'Upcoming', hi: 'Aane wali' },
  nextTag: { en: 'NEXT', hi: 'Agli' },
  yourBookings: { en: 'Your bookings', hi: 'Aapki bookings' },
  nothingDue: { en: 'Nothing due right now', hi: 'Abhi koi payment baaki nahi hai' },
  nothingDueNote: {
    en: 'All your instalments are paid. Enjoy your trip!',
    hi: 'Aapki saari instalments bhar di gayi hain. Trip enjoy karein!',
  },
  unknown: { en: "We couldn't find this number", hi: 'Yeh number humare paas registered nahi hai' },
  unknownNote: {
    en: 'Check the number, or use the one you booked with.',
    hi: 'Number check karein, ya booking wala number daalein.',
  },
  error: { en: "Can't reach the server", hi: 'Server se connect nahi ho pa raha' },
  errorNote: {
    en: "We won't show any amount or date until we can confirm it.",
    hi: 'Jab tak confirm nahi hota, hum koi amount ya date nahi dikhayenge.',
  },
  retry: { en: 'Retry', hi: 'Dobara try karein' },
} satisfies Record<string, Label>;

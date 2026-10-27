import { useRef, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { fetchNextPayment, NextPaymentResult, PaymentItem } from './api';
import { L, Label } from './labels';

type ScreenState =
  | { kind: 'idle'; message?: Label }
  | { kind: 'loading' }
  | { kind: 'done'; result: NextPaymentResult };

export default function NextPaymentScreen() {
  const [phone, setPhone] = useState('');
  const [state, setState] = useState<ScreenState>({ kind: 'idle' });
  const lastPhone = useRef('');
  // Only the newest request may update the screen; slower, older replies are dropped.
  const requestId = useRef(0);

  async function load(number: string) {
    const id = ++requestId.current;
    lastPhone.current = number;
    // Loading replaces whatever was on screen: no old amount/date survives.
    setState({ kind: 'loading' });
    const result = await fetchNextPayment(number);
    if (id === requestId.current) setState({ kind: 'done', result });
  }

  function onCheck() {
    const number = phone.replace(/\s+/g, '');
    if (!number) {
      setState({ kind: 'idle', message: L.enterPhone });
      return;
    }
    load(number);
  }

  function onChangePhone(text: string) {
    setPhone(text);
    // A result belongs to the number it was fetched for. Editing the number
    // clears it so we never show one traveller's amount under another number.
    if (state.kind !== 'idle') {
      requestId.current++;
      setState({ kind: 'idle' });
    }
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
          <Bi label={L.title} enStyle={styles.title} />

          <View style={styles.form}>
            <Bi label={L.phone} enStyle={styles.fieldLabel} />
            <View style={styles.inputRow}>
              <TextInput
                testID="phone-input"
                value={phone}
                onChangeText={onChangePhone}
                onSubmitEditing={onCheck}
                placeholder="98XXXXXXXX"
                placeholderTextColor="#94A3B8"
                keyboardType="phone-pad"
                returnKeyType="search"
                maxLength={15}
                style={styles.input}
                accessibilityLabel="Phone number"
              />
              <Pressable
                testID="check-button"
                onPress={onCheck}
                disabled={state.kind === 'loading'}
                style={({ pressed }) => [
                  styles.button,
                  (pressed || state.kind === 'loading') && styles.buttonPressed,
                ]}
                accessibilityRole="button"
              >
                <Text style={styles.buttonText}>{L.check.en}</Text>
                <Text style={styles.buttonSub}>{L.check.hi}</Text>
              </Pressable>
            </View>
          </View>

          <Body state={state} onRetry={() => load(lastPhone.current)} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Body({ state, onRetry }: { state: ScreenState; onRetry: () => void }) {
  if (state.kind === 'idle') {
    return state.message ? (
      <Bi label={state.message} enStyle={styles.validation} />
    ) : null;
  }

  if (state.kind === 'loading') {
    return (
      <View style={styles.centerBox} testID="state-loading">
        <ActivityIndicator size="large" color={C.brand} />
        <Bi label={L.loading} enStyle={styles.messageTitle} center />
      </View>
    );
  }

  const { result } = state;
  switch (result.status) {
    case 'ok':
      return <Payments next={result.next} bookings={result.bookings} />;

    case 'nothing_due':
      return (
        <MessageBox testID="state-nothing-due" icon="✓" tone="success" title={L.nothingDue} note={L.nothingDueNote} />
      );

    case 'unknown_number':
      return (
        <MessageBox testID="state-unknown" icon="?" tone="neutral" title={L.unknown} note={L.unknownNote} />
      );

    case 'error':
      return (
        <MessageBox testID="state-error" icon="!" tone="danger" title={L.error} note={L.errorNote}>
          <Pressable
            testID="retry-button"
            onPress={onRetry}
            style={({ pressed }) => [styles.retry, pressed && styles.buttonPressed]}
            accessibilityRole="button"
          >
            <Text style={styles.buttonText}>{L.retry.en}</Text>
            <Text style={styles.buttonSub}>{L.retry.hi}</Text>
          </Pressable>
        </MessageBox>
      );
  }
}

function Payments({ next, bookings }: { next: PaymentItem; bookings: PaymentItem[] }) {
  // The API orders bookings like the "next" query; we still match by value so
  // the highlight never depends on ordering.
  const nextIndex = bookings.findIndex(
    (b) =>
      b.booking === next.booking &&
      b.amount === next.amount &&
      b.due_date === next.due_date &&
      b.overdue === next.overdue,
  );

  return (
    <View testID={bookings.length > 1 ? 'state-many' : 'state-one'}>
      <NextCard item={next} />

      {bookings.length > 1 && (
        <View style={styles.listBox}>
          <Bi label={L.yourBookings} enStyle={styles.sectionTitle} />
          {bookings.map((b, i) => (
            <BookingRow key={`${b.booking}-${b.due_date}-${i}`} item={b} isNext={i === nextIndex} />
          ))}
        </View>
      )}
    </View>
  );
}

function NextCard({ item }: { item: PaymentItem }) {
  return (
    <View
      testID="next-card"
      style={[styles.card, styles.nextCard, item.overdue && styles.cardOverdue]}
    >
      <View style={styles.cardHeader}>
        <Bi label={L.nextPayment} enStyle={styles.cardHeading} />
        <StatusBadge overdue={item.overdue} />
      </View>

      <Field label={L.trip} value={item.booking} big />
      <View style={styles.fieldsRow}>
        <Field label={L.amount} value={String(item.amount)} big danger={item.overdue} />
        <Field label={L.dueDate} value={item.due_date} big danger={item.overdue} />
      </View>

      {item.overdue && (
        <View style={styles.overdueNote}>
          <Bi label={L.overdueNote} enStyle={styles.overdueNoteText} />
        </View>
      )}
    </View>
  );
}

function BookingRow({ item, isNext }: { item: PaymentItem; isNext: boolean }) {
  return (
    <View style={[styles.row, isNext && styles.rowNext, item.overdue && styles.cardOverdue]}>
      <View style={styles.rowTop}>
        <Text style={styles.rowTrip}>{item.booking}</Text>
        <View style={styles.rowTags}>
          {isNext && (
            <View style={[styles.badge, { backgroundColor: C.brand }]}>
              <Text style={styles.badgeText}>
                {L.nextTag.en} · {L.nextTag.hi}
              </Text>
            </View>
          )}
          {item.overdue && <StatusBadge overdue />}
        </View>
      </View>
      <View style={styles.fieldsRow}>
        <Field label={L.amount} value={String(item.amount)} danger={item.overdue} />
        <Field label={L.dueDate} value={item.due_date} danger={item.overdue} />
      </View>
    </View>
  );
}

function StatusBadge({ overdue }: { overdue: boolean }) {
  const label = overdue ? L.overdue : L.upcoming;
  return (
    <View
      testID={overdue ? 'overdue-badge' : undefined}
      style={[styles.badge, { backgroundColor: overdue ? C.danger : C.successBg }]}
    >
      <Text style={[styles.badgeText, !overdue && { color: C.success }]}>
        {overdue ? '⚠ ' : ''}
        {label.en} · {label.hi}
      </Text>
    </View>
  );
}

function Field({
  label,
  value,
  big,
  danger,
}: {
  label: Label;
  value: string;
  big?: boolean;
  danger?: boolean;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldEn}>{label.en}</Text>
      <Text style={styles.fieldHi}>{label.hi}</Text>
      <Text style={[big ? styles.valueBig : styles.value, danger && { color: C.danger }]}>
        {value}
      </Text>
    </View>
  );
}

function MessageBox({
  testID,
  icon,
  tone,
  title,
  note,
  children,
}: {
  testID: string;
  icon: string;
  tone: 'success' | 'neutral' | 'danger';
  title: Label;
  note: Label;
  children?: React.ReactNode;
}) {
  const color = tone === 'success' ? C.success : tone === 'danger' ? C.danger : C.muted;
  return (
    <View testID={testID} style={[styles.card, styles.centerBox]}>
      <View style={[styles.icon, { borderColor: color }]}>
        <Text style={[styles.iconText, { color }]}>{icon}</Text>
      </View>
      <Bi label={title} enStyle={styles.messageTitle} center />
      <Bi label={note} enStyle={styles.messageNote} center />
      {children}
    </View>
  );
}

function Bi({ label, enStyle, center }: { label: Label; enStyle?: object; center?: boolean }) {
  return (
    <View style={styles.bi}>
      <Text style={[enStyle, center && styles.center]}>{label.en}</Text>
      <Text style={[styles.hi, center && styles.center]}>{label.hi}</Text>
    </View>
  );
}

const C = {
  bg: '#F4F6F8',
  card: '#FFFFFF',
  ink: '#0F172A',
  muted: '#64748B',
  border: '#E2E8F0',
  brand: '#0E7C66',
  brandSoft: '#E7F5F1',
  danger: '#C62828',
  dangerSoft: '#FDECEC',
  success: '#1B7F3B',
  successBg: '#E3F4E8',
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: C.bg },
  flex: { flex: 1 },
  container: { padding: 16, paddingBottom: 40, width: '100%', maxWidth: 520, alignSelf: 'center' },
  title: { fontSize: 26, fontWeight: '800', color: C.ink },
  bi: { marginBottom: 2 },
  hi: { fontSize: 13, color: C.muted, marginTop: 1 },
  center: { textAlign: 'center' },

  form: { marginTop: 20, marginBottom: 16 },
  fieldLabel: { fontSize: 14, fontWeight: '600', color: C.ink },
  inputRow: { flexDirection: 'row', gap: 8, marginTop: 8 },
  input: {
    flex: 1,
    minWidth: 0,
    backgroundColor: C.card,
    borderWidth: 1,
    borderColor: C.border,
    borderRadius: 10,
    paddingHorizontal: 14,
    fontSize: 18,
    color: C.ink,
    minHeight: 52,
  },
  button: {
    backgroundColor: C.brand,
    borderRadius: 10,
    paddingHorizontal: 18,
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: 52,
  },
  buttonPressed: { opacity: 0.6 },
  buttonText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  buttonSub: { color: '#DDF3EC', fontSize: 11 },
  validation: { color: C.danger, fontWeight: '600' },

  card: {
    backgroundColor: C.card,
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: C.border,
  },
  nextCard: { borderWidth: 2, borderColor: C.brand, backgroundColor: C.brandSoft },
  cardOverdue: { borderColor: C.danger, backgroundColor: C.dangerSoft },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 8,
  },
  cardHeading: { fontSize: 18, fontWeight: '800', color: C.ink },
  fieldsRow: { flexDirection: 'row', gap: 16 },
  field: { flex: 1, marginTop: 10 },
  fieldEn: { fontSize: 12, fontWeight: '600', color: C.muted, textTransform: 'uppercase' },
  fieldHi: { fontSize: 11, color: C.muted },
  value: { fontSize: 17, fontWeight: '700', color: C.ink, marginTop: 2 },
  valueBig: { fontSize: 24, fontWeight: '800', color: C.ink, marginTop: 2 },
  overdueNote: {
    marginTop: 14,
    padding: 10,
    borderRadius: 8,
    backgroundColor: '#fff',
    borderLeftWidth: 4,
    borderLeftColor: C.danger,
  },
  overdueNoteText: { color: C.danger, fontWeight: '700' },

  badge: { borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4 },
  badgeText: { color: '#fff', fontSize: 12, fontWeight: '700' },

  listBox: { marginTop: 22 },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: C.ink },
  row: {
    backgroundColor: C.card,
    borderRadius: 12,
    padding: 14,
    marginTop: 10,
    borderWidth: 1,
    borderColor: C.border,
  },
  rowNext: { borderWidth: 2, borderColor: C.brand },
  rowTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  rowTrip: { fontSize: 17, fontWeight: '700', color: C.ink },
  rowTags: { flexDirection: 'row', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' },

  centerBox: { alignItems: 'center', paddingVertical: 28, gap: 10 },
  icon: {
    width: 52,
    height: 52,
    borderRadius: 26,
    borderWidth: 3,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconText: { fontSize: 24, fontWeight: '900' },
  messageTitle: { fontSize: 18, fontWeight: '700', color: C.ink },
  messageNote: { fontSize: 14, color: C.ink },
  retry: {
    marginTop: 8,
    backgroundColor: C.brand,
    borderRadius: 10,
    paddingHorizontal: 28,
    paddingVertical: 10,
    alignItems: 'center',
  },
});

// The entry box (REQ-276, REQ-277, REQ-278): the user types one or more short entries, e.g. `F 250; SWG 340 yd`, separated
// by new lines or semicolons, presses Expand and reviews each entry expanded, or exactly why it cannot be read, then
// presses Save. The API splits the text, applies the rules and checks the review again at save time; this component only
// shows the results.
import React, { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, HStack, Link, Table, Tbody, Td, Text, Textarea, Th, Thead, Tr, VStack } from '@chakra-ui/react';
import { api } from '../api/client';
import { type ApiClient, type ExpandResult, saveEntries, useExpandAll } from './useExpand';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "2026-11-05" -> "5 Nov 2026" (the date is a calendar date from the API: no time zone conversion). */
export function formatDate(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number);
  return `${day} ${MONTHS[month - 1]} ${year}`;
}

/** "3 entries saved." or "3 entries saved, 1 not saved." (WI-048, product owner answers q1 and q3). */
export function savedMessage(saved: number, notSaved: number): string {
  const head = `${saved} ${saved === 1 ? 'entry' : 'entries'} saved`;
  return notSaved > 0 ? `${head}, ${notSaved} not saved.` : `${head}.`;
}

function ResultRow({ index, result }: { index: number; result: ExpandResult }) {
  const { entry } = result;
  return (
    <Tr>
      <Td isNumeric>{index}</Td>
      <Td fontFamily="mono">{result.typed}</Td>
      {result.ok && entry ? (
        <>
          <Td>{entry.merchant ?? '-'}</Td>
          <Td>{entry.category}</Td>
          <Td isNumeric>{entry.amount}</Td>
          <Td>{formatDate(entry.date)}</Td>
          <Td>{entry.note ?? ''}</Td>
        </>
      ) : (
        <Td colSpan={5} color="red.600">Error: {result.error}</Td>
      )}
    </Tr>
  );
}

function ResultTable({ results }: { results: ExpandResult[] }) {
  return (
    <Table size="sm" aria-label="Expanded entries">
      <Thead>
        <Tr><Th isNumeric>#</Th><Th>Typed</Th><Th>Merchant</Th><Th>Category</Th><Th isNumeric>Amount</Th><Th>Date</Th><Th>Note</Th></Tr>
      </Thead>
      <Tbody>
        {results.map((result, i) => <ResultRow key={i} index={i + 1} result={result} />)}
      </Tbody>
    </Table>
  );
}

type SaveState =
  | { kind: 'idle' }
  | { kind: 'saving' }
  | { kind: 'saved'; message: string; failed: ExpandResult[] }
  | { kind: 'refused'; message: string }
  | { kind: 'failed'; message: string };

export function EntryBox({ client = api }: { client?: ApiClient }) {
  const [text, setText] = useState('');
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [request, setRequest] = useState(0);
  const [save, setSave] = useState<SaveState>({ kind: 'idle' });
  const result = useExpandAll(submitted, client, request);
  // Only separators and spaces: nothing to expand (the API would answer 422).
  const blank = !text.replace(/[;\s]/g, '');
  const saving = save.kind === 'saving';

  const review = result.status === 'success' && result.data?.ok ? result.data.results ?? [] : null;
  // Save only what the user is looking at: a review of the text as it is now, with at least one valid entry.
  const canSave = review !== null && text === submitted && review.some((r) => r.ok) && !saving;

  const expand = (event: React.FormEvent) => {
    event.preventDefault();
    if (blank || saving) return;
    setSave({ kind: 'idle' });
    setSubmitted(text);
    setRequest((n) => n + 1);
  };

  const saveReview = async () => {
    if (!canSave || review === null || submitted === null) return;
    setSave({ kind: 'saving' });
    try {
      const answer = await saveEntries(submitted, review, client);
      if (!answer.ok) {
        setSave({ kind: 'refused', message: answer.error ?? '' });
        return;
      }
      const failed = answer.failed ?? [];
      setSave({ kind: 'saved', message: savedMessage(answer.saved ?? 0, failed.length), failed });
      setText(failed.map((f) => f.typed).join('\n')); // only the lines to fix stay; cleared when all were saved
      setSubmitted(null);
    } catch (e) {
      setSave({ kind: 'failed', message: e instanceof Error ? e.message : String(e) });
    }
  };

  return (
    <Box as="section" maxW="4xl" mx="auto" p={4}>
      <form onSubmit={expand}>
        <VStack align="stretch">
          <Textarea
            aria-label="Short entries"
            placeholder={'F 250; SWG 340 yd\nUBR 180 12/11 airport'}
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={5}
            fontFamily="mono"
            autoComplete="off"
            spellCheck={false}
          />
          <HStack>
            <Button type="submit" isDisabled={blank || saving}>Expand</Button>
            <Button colorScheme="green" onClick={saveReview} isDisabled={!canSave} isLoading={saving} loadingText="Saving">
              Save
            </Button>
          </HStack>
        </VStack>
      </form>
      <Box mt={4} aria-live="polite">
        {save.kind === 'saved' && (
          <Box mb={4}>
            <Text role="status" fontWeight="semibold">{save.message}</Text>
            {save.failed.map((f, i) => (
              <Text key={i} color="red.600"><Text as="span" fontFamily="mono">{f.typed}</Text>: Error: {f.error}</Text>
            ))}
          </Box>
        )}
        {save.kind === 'refused' && <Text role="alert" mb={4}>Error: {save.message}</Text>}
        {save.kind === 'failed' && <Text role="alert" mb={4}>Could not save the entries: {save.message}</Text>}
        {submitted !== null && result.status === 'loading' && <Text>Expanding…</Text>}
        {result.status === 'error' && <Text role="alert">Could not expand the entries: {result.error}</Text>}
        {review !== null && submitted !== null && <ResultTable results={review} />}
        {result.status === 'success' && result.data && !result.data.ok && <Text role="alert">Error: {result.data.error}</Text>}
      </Box>
      <Link as={RouterLink} to="/summary" display="inline-block" mt={6}>Monthly summary</Link>
    </Box>
  );
}

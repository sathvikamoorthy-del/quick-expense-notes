// The entry box (REQ-276, REQ-277): the user types one or more short entries, e.g. `F 250; SWG 340 yd`, separated by new
// lines or semicolons, presses Expand and sees each entry expanded, or exactly why it cannot be read. The API splits the
// text and applies the rules; this component only shows the results. REQ-278 (save) builds on this component.
import React, { useState } from 'react';
import { Box, Button, Table, Tbody, Td, Text, Textarea, Th, Thead, Tr, VStack } from '@chakra-ui/react';
import { api } from '../api/client';
import { type ApiClient, type ExpandResult, useExpandAll } from './useExpand';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "2026-11-05" -> "5 Nov 2026" (the date is a calendar date from the API: no time zone conversion). */
export function formatDate(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number);
  return `${day} ${MONTHS[month - 1]} ${year}`;
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

export function EntryBox({ client = api }: { client?: ApiClient }) {
  const [text, setText] = useState('');
  const [submitted, setSubmitted] = useState<string | null>(null);
  const result = useExpandAll(submitted, client);
  // Only separators and spaces: nothing to expand (the API would answer 422).
  const blank = !text.replace(/[;\s]/g, '');

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!blank) setSubmitted(text);
  };

  return (
    <Box as="section" maxW="4xl" mx="auto" p={4}>
      <form onSubmit={submit}>
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
          <Box><Button type="submit" isDisabled={blank}>Expand</Button></Box>
        </VStack>
      </form>
      <Box mt={4} aria-live="polite">
        {submitted !== null && result.status === 'loading' && <Text>Expanding…</Text>}
        {result.status === 'error' && <Text role="alert">Could not expand the entries: {result.error}</Text>}
        {result.status === 'success' && result.data?.ok && <ResultTable results={result.data.results ?? []} />}
        {result.status === 'success' && result.data && !result.data.ok && <Text role="alert">Error: {result.data.error}</Text>}
      </Box>
    </Box>
  );
}

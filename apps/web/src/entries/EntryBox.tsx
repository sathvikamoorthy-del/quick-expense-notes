// The entry box (REQ-276): the user types one short entry, e.g. `SWG 340 yd`, and sees what it stands for, or exactly why
// it cannot be read. REQ-277 (several entries) and REQ-278 (save) build on this component.
import React, { useState } from 'react';
import { Box, Button, HStack, Input, Table, Tbody, Td, Text, Th, Thead, Tr } from '@chakra-ui/react';
import { api } from '../api/client';
import { type ApiClient, type ExpandedEntry, useExpand } from './useExpand';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "2026-11-05" -> "5 Nov 2026" (the date is a calendar date from the API: no time zone conversion). */
export function formatDate(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number);
  return `${day} ${MONTHS[month - 1]} ${year}`;
}

function EntryTable({ entry }: { entry: ExpandedEntry }) {
  return (
    <Table size="sm" aria-label="Expanded entry">
      <Thead>
        <Tr><Th>Merchant</Th><Th>Category</Th><Th isNumeric>Amount</Th><Th>Date</Th><Th>Note</Th></Tr>
      </Thead>
      <Tbody>
        <Tr>
          <Td>{entry.merchant ?? '-'}</Td>
          <Td>{entry.category}</Td>
          <Td isNumeric>{entry.amount}</Td>
          <Td>{formatDate(entry.date)}</Td>
          <Td>{entry.note ?? ''}</Td>
        </Tr>
      </Tbody>
    </Table>
  );
}

export function EntryBox({ client = api }: { client?: ApiClient }) {
  const [text, setText] = useState('');
  const [submitted, setSubmitted] = useState<string | null>(null);
  const result = useExpand(submitted, client);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (text.trim()) setSubmitted(text);
  };

  return (
    <Box as="section" maxW="3xl" mx="auto" p={4}>
      <form onSubmit={submit}>
        <HStack>
          <Input
            aria-label="Short entry"
            placeholder="SWG 340 yd"
            value={text}
            onChange={(e) => setText(e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
          <Button type="submit" isDisabled={!text.trim()}>Expand</Button>
        </HStack>
      </form>
      <Box mt={4} aria-live="polite">
        {submitted !== null && result.status === 'loading' && <Text>Expanding…</Text>}
        {result.status === 'error' && <Text role="alert">Could not expand the entry: {result.error}</Text>}
        {result.status === 'success' && result.data?.ok && result.data.entry && <EntryTable entry={result.data.entry} />}
        {result.status === 'success' && result.data && !result.data.ok && <Text role="alert">Error: {result.data.error}</Text>}
      </Box>
    </Box>
  );
}

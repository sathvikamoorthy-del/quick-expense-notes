// The monthly summary (REQ-279, WI-049): one total per category that has entries in the month, and a grand total.
// The page opens on the current IST month (the API decides it), moves with Previous / Next, and cannot open a future month.
import React, { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, Heading, HStack, Link, Table, Tbody, Td, Text, Tfoot, Th, Thead, Tr } from '@chakra-ui/react';
import { api } from '../api/client';
import type { ApiClient } from '../entries/useExpand';
import { useSummary } from './useSummary';

const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

/** "2026-11" -> "November 2026". Calendar text only: no Date, so no time zone effects. */
export function monthLabel(month: string): string {
  const [year, m] = month.split('-').map(Number);
  return `${MONTH_NAMES[m - 1]} ${year}`;
}

/** "2026-01", -1 -> "2025-12"; "2026-12", +1 -> "2027-01". */
export function shiftMonth(month: string, by: number): string {
  const [year, m] = month.split('-').map(Number);
  const index = year * 12 + (m - 1) + by;
  return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, '0')}`;
}

export function MonthlySummary({ client = api }: { client?: ApiClient }) {
  const [month, setMonth] = useState<string | null>(null); // null: the current month, as the API sees it
  const result = useSummary(month, client);
  const data = result.status === 'success' ? result.data : null;
  const shown = data?.month ?? month;

  return (
    <Box as="section" maxW="2xl" mx="auto" p={4}>
      <HStack justify="space-between" mb={4}>
        <Button onClick={() => shown && setMonth(shiftMonth(shown, -1))} isDisabled={!shown}>Previous</Button>
        <Heading as="h1" size="md">{shown ? monthLabel(shown) : 'Monthly summary'}</Heading>
        <Button
          onClick={() => shown && setMonth(shiftMonth(shown, 1))}
          isDisabled={!data || data.month >= data.current_month}
        >
          Next
        </Button>
      </HStack>
      <Box aria-live="polite">
        {result.status === 'loading' && <Text>Loading…</Text>}
        {result.status === 'error' && <Text role="alert">Could not load the summary: {result.error}</Text>}
        {data && data.categories.length === 0 && <Text>No expenses in this month.</Text>}
        {data && data.categories.length > 0 && (
          <Table size="sm" aria-label={`Summary for ${monthLabel(data.month)}`}>
            <Thead>
              <Tr><Th>Category</Th><Th isNumeric>Total</Th></Tr>
            </Thead>
            <Tbody>
              {data.categories.map((c) => (
                <Tr key={c.code}><Td>{c.category}</Td><Td isNumeric>{c.total}</Td></Tr>
              ))}
            </Tbody>
            <Tfoot>
              <Tr><Th>Grand total</Th><Th isNumeric>{data.grand_total}</Th></Tr>
            </Tfoot>
          </Table>
        )}
      </Box>
      <HStack spacing={6} mt={6}>
        <Link as={RouterLink} to="/entries">Enter expenses</Link>
        <Link as={RouterLink} to="/saved-entries">Saved entries</Link>
      </HStack>
    </Box>
  );
}

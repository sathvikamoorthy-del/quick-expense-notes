// The saved-entries list (REQ-280, WI-052; REQ-281, WI-061): the user's entries of one month, newest date first, each
// editable in place by re-typing its short form, or deleted for good after an in-place confirmation. The API applies the
// rules (dates count from the day the entry was saved); this page only shows.
import React, { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, Heading, HStack, Input, Link, Table, Tbody, Td, Text, Th, Thead, Tr } from '@chakra-ui/react';
import { api } from '../api/client';
import { formatDate } from '../entries/EntryBox';
import type { ApiClient } from '../entries/useExpand';
import { monthLabel, shiftMonth } from '../summary/MonthlySummary';
import { deleteEntry, editEntry, type SavedEntry, useSavedEntries } from './useSavedEntries';

type Editing = { id: string; text: string; saving: boolean; error: string | null };
type Deleting = { id: string; busy: boolean; error: string | null };

function ConfirmDeleteRow({ entry, deleting, onConfirm, onCancel }: {
  entry: SavedEntry;
  deleting: Deleting;
  onConfirm(): void;
  onCancel(): void;
}) {
  return (
    <Tr>
      <Td fontFamily="mono">{entry.typed}</Td>
      <Td colSpan={6}>
        <HStack>
          <Text fontWeight="semibold">Delete this entry?</Text>
          <Button size="sm" colorScheme="red" onClick={onConfirm} isLoading={deleting.busy} loadingText="Deleting">Delete</Button>
          <Button size="sm" onClick={onCancel} isDisabled={deleting.busy}>Cancel</Button>
        </HStack>
        {deleting.error && <Text role="alert" color="red.600" mt={2}>{deleting.error}</Text>}
      </Td>
    </Tr>
  );
}

function EditRow({ editing, onChange, onSave, onCancel }: {
  editing: Editing;
  onChange(text: string): void;
  onSave(): void;
  onCancel(): void;
}) {
  return (
    <Tr>
      <Td colSpan={7}>
        <form onSubmit={(e) => { e.preventDefault(); onSave(); }}>
          <HStack>
            <Input
              aria-label="Edit entry"
              fontFamily="mono"
              value={editing.text}
              onChange={(e) => onChange(e.target.value)}
              autoComplete="off"
              spellCheck={false}
              autoFocus
            />
            <Button type="submit" colorScheme="green" isDisabled={!editing.text.trim()} isLoading={editing.saving} loadingText="Saving">
              Save
            </Button>
            <Button onClick={onCancel} isDisabled={editing.saving}>Cancel</Button>
          </HStack>
        </form>
        {editing.error && <Text role="alert" color="red.600" mt={2}>{editing.error}</Text>}
      </Td>
    </Tr>
  );
}

function EntryRow({ entry, onEdit, onDelete, canEdit }: { entry: SavedEntry; onEdit(): void; onDelete(): void; canEdit: boolean }) {
  return (
    <Tr>
      <Td fontFamily="mono">{entry.typed}</Td>
      <Td>{entry.merchant ?? '-'}</Td>
      <Td>{entry.category}</Td>
      <Td isNumeric>{entry.amount}</Td>
      <Td>{formatDate(entry.date)}</Td>
      <Td>{entry.note ?? ''}</Td>
      <Td>
        <HStack>
          <Button size="sm" onClick={onEdit} isDisabled={!canEdit}>Edit</Button>
          <Button size="sm" variant="outline" colorScheme="red" onClick={onDelete} isDisabled={!canEdit}>Delete</Button>
        </HStack>
      </Td>
    </Tr>
  );
}

export function SavedEntries({ client = api }: { client?: ApiClient }) {
  const [month, setMonth] = useState<string | null>(null); // null: the current month, as the API sees it
  const [editing, setEditing] = useState<Editing | null>(null);
  const [deleting, setDeleting] = useState<Deleting | null>(null);
  const [note, setNote] = useState<string | null>(null); // "The entry moved to …" or "Entry deleted."
  const result = useSavedEntries(month, client);
  const data = result.status === 'success' ? result.data : null;
  const shown = data?.month ?? month;
  const rowOpen = editing !== null || deleting !== null; // one row in edit or confirm mode at a time

  const go = (by: number) => {
    if (!shown) return;
    setEditing(null);
    setDeleting(null);
    setNote(null);
    setMonth(shiftMonth(shown, by));
  };

  const confirmDelete = async () => {
    if (!deleting || deleting.busy) return;
    setDeleting({ ...deleting, busy: true, error: null });
    try {
      await deleteEntry(deleting.id, client);
      setDeleting(null);
      setNote('Entry deleted.');
      result.reload();
    } catch (e) {
      setDeleting({ ...deleting, busy: false, error: `Could not delete the entry: ${e instanceof Error ? e.message : String(e)}` });
    }
  };

  const save = async () => {
    if (!editing || editing.saving) return;
    setEditing({ ...editing, saving: true, error: null });
    try {
      const answer = await editEntry(editing.id, editing.text, client);
      if (!answer.ok || !answer.entry) {
        setEditing({ ...editing, saving: false, error: `Error: ${answer.error ?? ''}` });
        return;
      }
      const newMonth = answer.entry.date.slice(0, 7);
      setNote(shown && newMonth !== shown ? `The entry moved to ${monthLabel(newMonth)}.` : null);
      setEditing(null);
      result.reload();
    } catch (e) {
      setEditing({ ...editing, saving: false, error: `Could not save the edit: ${e instanceof Error ? e.message : String(e)}` });
    }
  };

  return (
    <Box as="section" maxW="5xl" mx="auto" p={4}>
      <HStack justify="space-between" mb={4}>
        <Button onClick={() => go(-1)} isDisabled={!shown}>Previous</Button>
        <Heading as="h1" size="md">{shown ? monthLabel(shown) : 'Saved entries'}</Heading>
        <Button onClick={() => go(1)} isDisabled={!data || data.month >= data.current_month}>Next</Button>
      </HStack>
      <Box aria-live="polite">
        {note && <Text role="status" mb={4}>{note}</Text>}
        {result.status === 'loading' && <Text>Loading…</Text>}
        {result.status === 'error' && <Text role="alert">Could not load the saved entries: {result.error}</Text>}
        {data && data.entries.length === 0 && <Text>No saved entries in this month.</Text>}
        {data && data.entries.length > 0 && (
          <Table size="sm" aria-label={`Saved entries of ${monthLabel(data.month)}`}>
            <Thead>
              <Tr><Th>Typed</Th><Th>Merchant</Th><Th>Category</Th><Th isNumeric>Amount</Th><Th>Date</Th><Th>Note</Th><Th /></Tr>
            </Thead>
            <Tbody>
              {data.entries.map((entry) =>
                editing?.id === entry.id ? (
                  <EditRow
                    key={entry.id}
                    editing={editing}
                    onChange={(text) => setEditing({ ...editing, text })}
                    onSave={save}
                    onCancel={() => setEditing(null)}
                  />
                ) : deleting?.id === entry.id ? (
                  <ConfirmDeleteRow
                    key={entry.id}
                    entry={entry}
                    deleting={deleting}
                    onConfirm={confirmDelete}
                    onCancel={() => setDeleting(null)}
                  />
                ) : (
                  <EntryRow
                    key={entry.id}
                    entry={entry}
                    canEdit={!rowOpen}
                    onEdit={() => { setNote(null); setEditing({ id: entry.id, text: entry.edit_text, saving: false, error: null }); }}
                    onDelete={() => { setNote(null); setDeleting({ id: entry.id, busy: false, error: null }); }}
                  />
                ))}
            </Tbody>
          </Table>
        )}
      </Box>
      <HStack spacing={6} mt={6}>
        <Link as={RouterLink} to="/entries">Enter expenses</Link>
        <Link as={RouterLink} to="/summary">Monthly summary</Link>
      </HStack>
    </Box>
  );
}

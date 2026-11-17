// S01 Sign in (REQ-275): email and password only. No sign-up, forgot password or other providers in this story.
import React, { useState } from 'react';
import { Box, Button, Flex, FormControl, FormLabel, Heading, Input, Text } from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { type ApiClient, signIn } from './useSession';

export function SignIn({ client = api }: { client?: ApiClient }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setBusy(true);
    const result = await signIn(email, password, client);
    setBusy(false);
    if (result.ok) navigate('/entries', { replace: true });
    else setError(result.error);
  };

  return (
    <Box as="main" maxW="md" mx="auto" mt={12} p={6} borderWidth="1px" borderRadius="md">
      <Heading as="h1" size="md">Quick Expense Notes</Heading>
      <Text mt={2} mb={6}>Sign in to see and change only your own expenses.</Text>
      <form onSubmit={submit} noValidate>
        <FormControl mb={4}>
          <FormLabel>Email</FormLabel>
          <Input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} />
        </FormControl>
        <FormControl mb={4}>
          <FormLabel>Password (at least 8 characters)</FormLabel>
          <Input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </FormControl>
        {error && <Text role="alert" color="red.600" mb={4}>{error}</Text>}
        <Flex justify="flex-end">
          <Button type="submit" isLoading={busy}>Sign in</Button>
        </Flex>
      </form>
    </Box>
  );
}

// Guards the pages that need a signed-in user (REQ-275): signed out, they show the Sign in screen instead.
// Signed in, the S02 header (email and Sign out) sits above the page.
import React from 'react';
import { Button, Flex, Heading, Spacer, Text } from '@chakra-ui/react';
import { Navigate } from 'react-router-dom';
import { signOut, useSession } from './useSession';

export function RequireAuth({ children }: { children?: React.ReactNode }) {
  const user = useSession((s) => s.user);
  if (!user) return <Navigate to="/sign-in" replace />;
  return (
    <>
      <Flex as="header" align="center" gap={4} px={4} py={2} borderBottomWidth="1px">
        <Heading as="h1" size="md">Quick Expense Notes</Heading>
        <Spacer />
        <Text>{user.email}</Text>
        <Button size="sm" onClick={signOut}>Sign out</Button>
      </Flex>
      {children}
    </>
  );
}

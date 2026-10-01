/**
 * Target of the OIDC redirect `stadtfest://auth`. expo-auth-session consumes the redirect;
 * on Android expo-router may still open this route, so it only returns to the previous screen.
 */
import {router} from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import {useEffect} from 'react';

WebBrowser.maybeCompleteAuthSession();

export default function AuthRedirect() {
  useEffect(() => {
    if (router.canGoBack()) router.back();
    else router.replace('/');
  }, []);
  return null;
}

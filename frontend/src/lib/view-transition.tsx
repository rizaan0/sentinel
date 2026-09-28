import { useEffect } from "react";
import {
  Link as RouterLink,
  NavLink as RouterNavLink,
  useNavigate as useRouterNavigate,
  type LinkProps,
  type NavLinkProps,
  type NavigateProps,
  type NavigateFunction,
  type NavigateOptions,
  type To,
} from "react-router-dom";

/**
 * Same document View Transitions behavior as next-view-transitions.
 * That package imports next/link and next/navigation, so it cannot run in this Vite app.
 * React Router calls document.startViewTransition when viewTransition is set,
 * and replays it on back/forward for pairs that animated on the way in.
 */
function motionOk() {
  return (
    typeof document !== "undefined" &&
    "startViewTransition" in document &&
    !window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function Link({ viewTransition, ...props }: LinkProps) {
  return <RouterLink {...props} viewTransition={viewTransition ?? motionOk()} />;
}

export function NavLink({ viewTransition, ...props }: NavLinkProps) {
  return <RouterNavLink {...props} viewTransition={viewTransition ?? motionOk()} />;
}

export function Navigate({ to, replace, state, relative }: NavigateProps) {
  const navigate = useRouterNavigate();
  const path = JSON.stringify(to);
  useEffect(() => {
    navigate(JSON.parse(path) as To, {
      replace,
      state,
      relative,
      viewTransition: motionOk(),
    });
  }, [navigate, path, replace, state, relative]);
  return null;
}

export function useNavigate(): NavigateFunction {
  const navigate = useRouterNavigate();
  return ((to: To | number, options?: NavigateOptions) => {
    if (typeof to === "number") {
      navigate(to);
      return;
    }
    navigate(to, { viewTransition: motionOk(), ...options });
  }) as NavigateFunction;
}

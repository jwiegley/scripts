#!/usr/bin/env runhaskell

module Archiver where

{- Archiver, version 1.0

   by John Wiegley <johnw@newartisans.com>

   Usage: archive [OPTION...] <FILE | DIRECTORY>...

   Archives a file or directory by compressing it (if need be) and moving it
   to my ~/Archives/Inbox folder.

   Several thing happen during the course of this operation:

    1. If the file has the exention ".dmg", then it will be converted to a
       disk image with bzip2 internal compression, using hdiutil.

    2. If the file is already compressed by another means, it won't be
       compressed further.

    3. If compression occurred, and the compressed name is different from the
       original, the original is deleted.  NOTE: If the -s flag was given the
       original is securely deleted.

    4. If the -l flag is given, the file is not moved.

    5. After all is done, and the file (possibly) moved, it will have its SHA1
       checksum saved as an extended attribute. -}

import System
import System.Console.GetOpt
import System.Directory
import System.Environment
import Control.Monad

{- Options supported by this script:

   `-l` causes the destination archive not to be moved into ~/Archives/Inbox.

   `-s` causes the original file (if different from the final archive name) to
   be securely removed. -}

data Flag = Local | Secure deriving (Eq, Show)

options :: [OptDescr Flag]
options = [ Option ['l'] ["local"] (NoArg Local)  "Don't move archive file"
          , Option ['s'] ["secure"] (NoArg Secure) "Securely remove original"
          ]

archiveOpts :: [String] -> IO ([Flag], [String])
archiveOpts argv =
    case getOpt Permute options argv of
             (o, n, []  ) -> return (o,n)
             (_, _, errs) -> ioError (userError (concat errs ++ usageInfo header options))
        where header = "Usage: archive [OPTION...] <FILE | DIRECTORY>..."

-- Apply the `archiveItem` function for every argument passed in.

main :: IO ()
main = do
  cmdArgs <- getArgs
  (flags, args) <- archiveOpts cmdArgs
  mapM (archiveItem flags) args
  return ()

{- Archive an item by first compression it, resulting in two pathnames: The
   original item, and the result.  If not Local, move the result to
   ~/Archives/Inbox.  If original name != result name, remove the original,
   doing so securely if Secure. -}

archiveItem :: [Flag] -> FilePath -> IO ()
archiveItem flags fp = do
  compressItem fp

  if Local `elem` flags
     then return ()
     else do
       home <- getEnv "HOME"
       invoke ("mv " ++ escapePath fp ++ " " ++ home ++ "/Archives/Inbox")

  if Secure `elem` flags
     then invoke ("srm -mvf " ++ escapePath fp)
     else removeItem fp

compressItem :: FilePath -> IO ()
compressItem fp = do
  return ()

removeItem :: FilePath -> IO ()
removeItem fp = do
  isdir <- doesDirectoryExist fp
  if isdir
     then removeDirectory fp
     else removeFile fp

-- Return a pathname escaped in double-quotes
escapePath :: FilePath -> String
escapePath fp = '"' : escape fp
    where escape []        = ['"']
          escape ('\\':xs) = '\\' : '\\' : escape xs
          escape ('"':xs)  = '\\' : '"' : escape xs
          escape (x:xs)    = x : escape xs

compressDir :: FilePath -> String
compressDir fp = "tar cf - " ++ escapePath fp
                 ++ "| 7za a " ++ escapePath fp ++ ".tar.7z -si"

invoke :: String -> IO ()
invoke command = do
  exitcode <- system command
  case exitcode of
    ExitSuccess      -> return ()
    ExitFailure code ->
        ioError (userError ("Command failed [exit "
                            ++ show code ++ "]: " ++ command))

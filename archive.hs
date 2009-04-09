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

import Data.List
import qualified Data.ByteString as BS
import Text.Printf
import System.Console.GetOpt
import System.Directory
import System.Environment
import System.FilePath.Posix
import Control.Monad
import Control.Exception
import HSH
import HSH.ShellEquivs

{- Options supported by this script:

   `-l` causes the destination archive not to be moved into ~/Archives/Inbox.

   `-s` causes the original file (if different from the final archive name) to
   be securely removed. -}

data Flag = Local | Secure | Image deriving (Eq, Show)

options :: [OptDescr Flag]
options = [ Option ['l'] ["local"] (NoArg Local)  "Don't move archive file"
          , Option ['s'] ["secure"] (NoArg Secure) "Securely remove original"
          , Option ['i'] ["image"] (NoArg Image) "Place item in a .dmg image"
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

shell :: String -> [String] -> IO ()
shell cmd args = runIO $ (cmd, args)

{- Archive an item by first compression it, resulting in two pathnames: The
   original item, and the result.  If not Local, move the result to
   ~/Archives/Inbox. Remove all temporaries and old files. -}

removeItems :: [Flag] -> [FilePath] -> IO ()
removeItems flags fps = do
  forM fps $ \fp -> do
      fexists <- doesFileExist fp
      dexists <- doesDirectoryExist fp
      if fexists || dexists
         then if Secure `elem` flags
                 then shell "srm" ["-mfr", fp]
                 else shell "rm"  ["-fr", fp]
         else return ()
  return ()

archiveItem :: [Flag] -> FilePath -> IO ()
archiveItem flags fp = do
  nfp <- compressItem flags fp

  if Local `elem` flags
     then do
       finalDest <- safeMove nfp $ dirname fp </> basename nfp
       recordChecksum finalDest
     else do
       (inbox:[]) <- glob "~/Archives/Inbox"
       let dest = (inbox </> basename nfp)
       finalDest <- safeMove nfp dest
       recordChecksum finalDest
  return ()

safeMove :: FilePath -> FilePath -> IO FilePath
safeMove src dst = do
  safeDest <- findUniqueName 0 dst
  renameFile src safeDest
  return safeDest

findUniqueName :: Int -> FilePath -> IO FilePath
findUniqueName n fp = do
  let name = if n == 0
             then fp
             else dropExtension fp ++ "." ++ show n ++
                  takeExtension fp
  exists <- doesFileExist name
  if exists
     then findUniqueName (n+1) fp
     else return name

compressItem :: [Flag] -> FilePath -> IO FilePath
compressItem flags fp = do
  isdir <- doesDirectoryExist fp
  exists <- doesFileExist fp
  if not isdir && not exists
     then fail $ "Item does not exist: " ++ fp
     else do
       if Image `elem` flags
          then makeDiskImage flags fp
          else do
            let ext = takeExtension fp
            if isdir
               then do
                 case ext of
                   ".app" -> makeDiskImage flags fp
                   ".pkg" -> makeDiskImage flags fp
                   _      -> compressDirectory flags fp
               else do
                 case ext of
                   ".7z"  -> return fp
                   ".gz"  -> recompressFile flags fp
                   ".bz2" -> recompressFile flags fp
                   ".zip" -> recompressZip flags fp
                   ".dmg" -> compressDiskImage flags fp
                   ".pkg" -> makeDiskImage flags fp
                   _      -> compressFile flags fp

compressDirectory :: [Flag] -> FilePath -> IO FilePath
compressDirectory flags fp = do
  let nfp = fp ++ ".tar.7z"
  onException
    (bracketCD (dirname fp)
       (do runIO $ ("tar", ["cf", "-", basename fp]) -|-
                   ("7za", ["a", nfp, "-si"])
           removeItems flags [fp]
           return nfp))
    (removeItems flags [nfp])
          
makeDiskImage :: [Flag] -> FilePath -> IO FilePath
makeDiskImage flags fp = do
  let root = dropExtension fp
  mkdir root 0o755
  onException (shell "mv" [fp, root]) (removeItems flags [root])
  let nfp = root ++ ".dmg"
  onException
    (do shell "hdiutil" ["create", "-srcfolder", root, nfp]
        removeItems flags [root, fp]
        compressDiskImage flags nfp)
    (removeItems flags [root, nfp])

compressDiskImage :: [Flag] -> FilePath -> IO FilePath
compressDiskImage flags fp = do
  tempPath <- getTemporaryDirectory
  let base = basename fp
      temp = tempPath </> base
  onException
    (do shell "hdiutil" ["convert", "-format", "UDBZ", "-o", temp, fp]
        removeItems flags [fp]
        return temp)
    (removeItems flags [temp])

compressFile :: [Flag] -> FilePath -> IO FilePath
compressFile flags fp = do
  let nfp = fp ++ ".7z"
  onException
    (bracketCD
       (dirname fp) $ do shell "7za" ["a", nfp, basename fp]
                         removeItems flags [fp]
                         return nfp)
    (removeItems flags [nfp])

fileChecksum :: FilePath -> IO BS.ByteString
fileChecksum fp = run $ ("openssl", ["sha1", "-binary", fp])

hexString :: BS.ByteString -> String
hexString = concat . map (printf "%02x") . BS.unpack

recordChecksum :: FilePath -> IO ()
recordChecksum fp = do
  csum <- fileChecksum fp
  shell "xattr" ["-w", "checksum-sha1", hexString csum, fp]

recompressFile :: [Flag] -> FilePath -> IO FilePath
recompressFile flags fp = uncompressFile fp >>= compressFile flags

uncompressFile :: FilePath -> IO FilePath
uncompressFile fp = do
  let ext = takeExtension fp
  case ext of
    ".gz"  -> (shell "gzip" ["-d", fp]  >> return (dropExtension fp))
    ".bz2" -> (shell "bzip2" ["-d", fp] >> return (dropExtension fp))
    _      -> fail $ "Unknown file extension: " ++ ext

recompressZip :: [Flag] -> FilePath -> IO FilePath
recompressZip flags fp = do
  tempPath <- getTemporaryDirectory
  let base = (dropExtension . basename) fp
      temp = tempPath </> base
  shell "unzip" ["-d", temp, fp]
  allFiles <- getDirectoryContents temp
  let files = allFiles \\ [".", ".."]
  -- Always remove the "temp" directory
  finally
    (case length files of
       0 -> return fp
       1 -> do nfp <- compressItem flags $ temp </> head files
               let nnfp = tempPath </> basename nfp
               renameFile nfp nnfp -- get it out of the "temp" dir
               return nnfp
       _ -> compressDirectory flags temp)
    (removeItems flags [temp])
